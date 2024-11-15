import logging
from abc import ABC, abstractmethod
from inspect import signature
from pathlib import Path
from typing import (
    Any,
    Callable,
    Optional,
    Type,
    Union,
    List,
    Literal,
    Dict,
    TypeVar,
    Generic,
)
from functools import reduce
from pydantic import BaseModel
from dataclasses import dataclass, field
from enum import Enum

from healthchain.io.base import BaseConnector
from healthchain.io.containers import DataContainer
from healthchain.pipeline.components.base import BaseComponent

logger = logging.getLogger(__name__)

T = TypeVar("T")


# TODO: dynamic resolution, maybe
PositionType = Literal["first", "last", "default", "after", "before"]


class ModelSource(Enum):
    """Enumeration of supported model sources"""

    SPACY = "spacy"
    HUGGINGFACE = "huggingface"
    LANGCHAIN = "langchain"


@dataclass
class ModelConfig:
    """Configuration for model initialization"""

    source: ModelSource
    model_id: Optional[str] = None
    pipeline_object: Optional[Any] = None
    task: Optional[str] = None
    path: Optional[Path] = None
    kwargs: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineNode(Generic[T]):
    """
    Represents a node in a pipeline.

    Attributes:
        func (Callable[[DataContainer[T]], DataContainer[T]]): The function to be applied to the data.
        position (PositionType, optional): The position of the node in the pipeline. Defaults to "default".
        reference (str, optional): The reference for the relative position of the node. Name should be the "name" attribute of another node. Defaults to None.
        stage (str, optional): The stage of the node in the pipeline. Group nodes by stage e.g. "preprocessing". Defaults to None.
        name (str, optional): The name of the node. Defaults to None.
        dependencies (List[str], optional): The list of dependencies for the node. Defaults to an empty list.
    """

    func: Callable[[DataContainer[T]], DataContainer[T]]
    position: PositionType = "default"
    reference: str = None
    stage: str = None
    name: str = None
    dependencies: List[str] = field(default_factory=list)


class BasePipeline(Generic[T], ABC):
    """
    Abstract base class for creating and managing data processing pipelines.

    The BasePipeline class provides a framework for building modular data processing pipelines
    by allowing users to add, remove, and configure components with defined dependencies and
    execution order. Components can be added at specific positions, grouped into stages, and
    connected via input/output connectors.

    This is an abstract base class that should be subclassed to create specific pipeline
    implementations.

    Attributes:
        _components (List[PipelineNode[T]]): Ordered list of pipeline components
        _stages (Dict[str, List[Callable]]): Components grouped by processing stage
        _built_pipeline (Optional[Callable]): Compiled pipeline function
        _input_connector (Optional[BaseConnector[T]]): Connector for processing input data
        _output_connector (Optional[BaseConnector[T]]): Connector for processing output data
        _output_template (Optional[str]): Template string for formatting pipeline outputs
        _model_config (Optional[ModelConfig]): Configuration for the pipeline model

    Example:
        >>> class MyPipeline(BasePipeline[str]):
        ...     def configure_pipeline(self, config: ModelConfig) -> None:
        ...         self.add_node(preprocess, stage="preprocessing")
        ...         self.add_node(process, stage="processing")
        ...         self.add_node(postprocess, stage="postprocessing")
        ...
        >>> pipeline = MyPipeline()
        >>> result = pipeline("input text")
    """

    def __init__(self):
        self._components: List[PipelineNode[T]] = []
        self._stages: Dict[str, List[Callable]] = {}
        self._built_pipeline: Optional[Callable] = None
        self._input_connector: Optional[BaseConnector[T]] = None
        self._output_connector: Optional[BaseConnector[T]] = None
        self._output_template: Optional[str] = None
        self._output_template_path: Optional[Path] = None

    def __repr__(self) -> str:
        components_repr = ", ".join(
            [f'"{component.name}"' for component in self._components]
        )
        return f"[{components_repr}]"

    def _configure_output_templates(
        self,
        template: Optional[str] = None,
        template_path: Optional[Union[str, Path]] = None,
    ) -> None:
        """
        Configure template settings for the pipeline.

        Args:
            template (Optional[str]): Template string for formatting outputs.
                Defaults to None.
            template_path (Optional[Union[str, Path]]): Path to template file.
                Defaults to None.
        """
        self._output_template = template
        self._output_template_path = Path(template_path) if template_path else None

    @classmethod
    def load(
        cls,
        pipeline: Callable,
        source: str,
        task: Optional[str] = "text-generation",
        template: Optional[str] = None,
        template_path: Optional[Union[str, Path]] = None,
        **kwargs: Any,
    ) -> "BasePipeline":
        """
        Load a pipeline from a pre-built pipeline object (e.g. LangChain chain or HuggingFace pipeline).

        Args:
            pipeline (Callable): A callable pipeline object (e.g. LangChain chain, HuggingFace pipeline)
            source (str): Source of the pipeline. Can be "langchain" or "huggingface".
            task (Optional[str]): Task identifier used to retrieve model outputs.
                Defaults to "text-generation".
            template (Optional[str]): Template string for formatting outputs.
                Defaults to None.
            template_path (Optional[Union[str, Path]]): Path to template file.
                Defaults to None.
            **kwargs: Additional configuration options passed to the pipeline.

        Returns:
            BasePipeline: Configured pipeline instance.

        Raises:
            ValueError: If pipeline is not callable or source is invalid.

        Examples:
            >>> # Load LangChain pipeline
            >>> from langchain_core.prompts import ChatPromptTemplate
            >>> from langchain_openai import ChatOpenAI
            >>> chain = ChatPromptTemplate.from_template("What is {input}?") | ChatOpenAI()
            >>> pipeline = Pipeline.load(chain, source="langchain", temperature=0.7)
            >>>
            >>> # Load HuggingFace pipeline
            >>> from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
            >>> tokenizer = AutoTokenizer.from_pretrained("gpt2")
            >>> model = AutoModelForCausalLM.from_pretrained("gpt2")
            >>> pipe = pipeline("text-generation", model=model, tokenizer=tokenizer, max_new_tokens=10)
            >>> pipeline = Pipeline.load(pipe, source="huggingface")
        """
        if not (hasattr(pipeline, "__call__") or hasattr(pipeline, "invoke")):
            raise ValueError("Pipeline must be a callable object")

        # Validate source
        source = source.lower()
        if source not in ["langchain", "huggingface"]:
            raise ValueError(
                "Source must be either 'langchain' or 'huggingface' for direct pipeline loading"
            )

        # For HuggingFace pipelines, try to infer task if not provided
        if source == "huggingface" and hasattr(pipeline, "task") and not task:
            task = pipeline.task

        instance = cls()
        instance._configure_output_templates(template, template_path)

        config = ModelConfig(
            source=ModelSource(source),
            pipeline_object=pipeline,
            task=task,
            kwargs=kwargs,
        )

        instance._model_config = config
        instance.configure_pipeline(config)

        return instance

    @classmethod
    def from_model_id(
        cls,
        model_id: str,
        source: Union[str, ModelSource] = "huggingface",
        task: Optional[str] = "text-generation",
        template: Optional[str] = None,
        template_path: Optional[Union[str, Path]] = None,
        **kwargs: Any,
    ) -> "BasePipeline":
        """
        Load pipeline from a model identifier.

        Args:
            model_id (str): Model identifier (e.g. HuggingFace model ID, SpaCy model name)
            source (Union[str, ModelSource]): Model source. Defaults to "huggingface".
                Can be "huggingface", "spacy".
            task (Optional[str]): Task identifier for the model. Defaults to "text-generation".
            template (Optional[str]): Optional template string for formatting model output.
            template_path (Optional[Union[str, Path]]): Optional path to template file for formatting model output.
            **kwargs: Additional configuration options passed to the model. e.g. temperature, max_length, etc.

        Returns:
            BasePipeline: Configured pipeline instance.

        Raises:
            ValueError: If source is not a valid ModelSource.

        Examples:
            >>> # Load HuggingFace model
            >>> pipeline = Pipeline.from_model_id(
            ...     "facebook/bart-large-cnn",
            ...     task="summarization",
            ...     temperature=0.7
            ... )
            >>>
            >>> # Load SpaCy model
            >>> pipeline = Pipeline.from_model_id(
            ...     "en_core_sci_md",
            ...     source="spacy",
            ...     disable=["parser"]
            ... )
            >>>
            >>> # Load with output template
            >>> template = '''{"summary": "{{ model_output }}"}'''
            >>> pipeline = Pipeline.from_model_id(
            ...     "gpt-3.5-turbo",
            ...     source="huggingface",
            ...     template=template
            ... )
        """
        pipeline = cls()
        pipeline._configure_output_templates(template, template_path)

        config = ModelConfig(
            source=ModelSource(source.lower()),
            model_id=model_id,
            task=task,
            kwargs=kwargs,
        )
        pipeline._model_config = config
        pipeline.configure_pipeline(config)

        return pipeline

    @classmethod
    def from_local_model(
        cls,
        path: Union[str, Path],
        source: Union[str, ModelSource],
        task: Optional[str] = None,
        template: Optional[str] = None,
        template_path: Optional[Union[str, Path]] = None,
        **kwargs: Any,
    ) -> "BasePipeline":
        """Load pipeline from a local model path.

        Args:
            path (Union[str, Path]): Path to local model files/directory
            source (Union[str, ModelSource]): Model source (e.g. "huggingface", "spacy")
            task (Optional[str]): Task identifier for the model. Defaults to None.
            template (Optional[str]): Optional template string for formatting model output.
            template_path (Optional[Union[str, Path]]): Optional path to template file for formatting model output.
            **kwargs: Additional configuration options passed to the model. e.g. temperature, max_length, etc.

        Returns:
            BasePipeline: Configured pipeline instance.

        Raises:
            ValueError: If source is not a valid ModelSource.

        Examples:
            >>> # Load local HuggingFace model
            >>> pipeline = Pipeline.from_local_model(
            ...     "models/my_summarizer",
            ...     source="huggingface",
            ...     task="summarization",
            ...     temperature=0.7
            ... )
            >>>
            >>> # Load local SpaCy model
            >>> pipeline = Pipeline.from_local_model(
            ...     "models/en_core_sci_md",
            ...     source="spacy",
            ...     disable=["parser"]
            ... )
            >>>
            >>> # Load with output template
            >>> template = '''{"summary": "{{ model_output }}"}'''
            >>> pipeline = Pipeline.from_local_model(
            ...     "models/gpt_model",
            ...     source="huggingface",
            ...     template=template
            ... )
        """
        pipeline = cls()
        pipeline._configure_output_templates(template, template_path)

        path = Path(path)
        config = ModelConfig(
            source=ModelSource(source.lower()),
            model_id=path.name,
            path=path,
            task=task,
            kwargs=kwargs,
        )
        pipeline._model_config = config
        pipeline.configure_pipeline(config)

        return pipeline

    @abstractmethod
    def configure_pipeline(self, model_config: ModelConfig) -> None:
        """
        Configure the pipeline based on the provided model configuration.

        This method should be implemented by subclasses to add specific components
        and configure the pipeline according to the given model configuration.
        The configuration typically involves:
        1. Setting up input/output connectors
        2. Adding model components based on the model source
        3. Adding any additional processing nodes
        4. Configuring the pipeline stages and execution order

        Args:
            model_config (ModelConfig): Configuration object containing:
                - source: Model source (e.g. huggingface, spacy, langchain)
                - model: Model identifier or path
                - task: Optional task name (e.g. summarization, ner)
                - path: Optional local path to model files
                - kwargs: Additional model configuration parameters

        Returns:
            None

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.

        Example:
            >>> def configure_pipeline(self, config: ModelConfig):
            ...     # Add FHIR connector for input/output
            ...     connector = FhirConnector()
            ...     self.add_input(connector)
            ...
            ...     # Add model component
            ...     model = self.get_model_component(config)
            ...     self.add_node(model, stage="processing")
            ...
            ...     # Add output formatting
            ...     self.add_node(OutputFormatter(), stage="formatting")
            ...     self.add_output(connector)
        """
        raise NotImplementedError("This method must be implemented by subclasses.")

    @property
    def stages(self):
        """
        Returns a human-readable representation of the pipeline stages.
        """
        output = ["Pipeline Stages:"]
        for stage, components in self._stages.items():
            output.append(f"  {stage}:")
            for component in components:
                component_name = (
                    component.__name__
                    if hasattr(component, "__name__")
                    else (
                        component.__class__.__name__
                        if hasattr(component, "__class__")
                        else str(component)
                    )
                )
                output.append(f"    - {component_name}")
        if not self._stages:
            output.append("  No stages defined.")
        return "\n".join(output)

    @stages.setter
    def stages(self, new_stages: Dict[str, List[Callable]]):
        """
        Sets the stages of the pipeline.

        Args:
            new_stages (Dict[str, List[Callable]]): A dictionary where keys are stage names
                                                    and values are lists of callable components.
        """
        self._stages = new_stages

    def add_input(self, connector: BaseConnector[T]) -> None:
        """
        Adds an input connector to the pipeline.

        This method sets the input connector for the pipeline, which is responsible
        for processing the input data before it's passed to the pipeline components.

        Args:
            connector (Connector[T]): The input connector to be added to the pipeline.

        Returns:
            None

        Note:
            Only one input connector can be set for the pipeline. If this method is
            called multiple times, the last connector will overwrite the previous ones.
        """
        self._input_connector = connector

    def add_output(self, connector: BaseConnector[T]) -> None:
        """
        Adds an output connector to the pipeline.

        This method sets the output connector for the pipeline, which is responsible
        for processing the output data after it has passed through all pipeline components.

        Args:
            connector (Connector[T]): The output connector to be added to the pipeline.

        Returns:
            None

        Note:
            Only one output connector can be set for the pipeline. If this method is
            called multiple times, the last connector will overwrite the previous ones.
        """
        self._output_connector = connector

    def add_node(
        self,
        component: Union[
            BaseComponent[T], Callable[[DataContainer[T]], DataContainer[T]]
        ] = None,
        *,
        position: PositionType = "default",
        reference: str = None,
        stage: str = None,
        name: str = None,
        input_model: Type[BaseModel] = None,
        output_model: Type[BaseModel] = None,
        dependencies: List[str] = [],
    ) -> None:
        """
        Adds a component node to the pipeline.

        Args:
            component (Union[BaseComponent[T], Callable[[DataContainer[T]], DataContainer[T]]], optional):
                The component to be added. It can be either a BaseComponent object or a callable function.
                Defaults to None.
            position (PositionType, optional):
                The position at which the component should be added in the pipeline.
                Valid values are "default", "first", "last", "after", and "before".
                Defaults to "default".
            reference (str, optional):
                The name of the component after or before which the new component should be added.
                Only applicable when position is "after" or "before".
                Defaults to None.
            stage (str, optional):
                The stage to which the component belongs.
                Defaults to None.
            name (str, optional):
                The name of the component.
                Defaults to None, in which case the name of the function will be used.
            input_model (Type[BaseModel], optional):
                The input Pydantic model class for validating the input data.
                Defaults to None.
            output_model (Type[BaseModel], optional):
                The output Pydantic model class for validating the output data.
                Defaults to None.
            dependencies (List[str], optional):
                The list of component names that this component depends on.
                Defaults to an empty list.

        Returns:
            The original component if component is None, otherwise the wrapper function.

        """

        def wrapper(func):
            def validated_component(data: DataContainer[T]) -> DataContainer[T]:
                # Validate input if input_model is provided
                if input_model:
                    input_model(**data.__dict__)

                # Run the component
                result = func(data)

                # Validate output if output_model is provided
                if output_model:
                    output_model(**result.__dict__)

                return result

            component_func = (
                validated_component if input_model or output_model else func
            )
            new_component = PipelineNode(
                func=component_func,
                position=position,
                reference=reference,
                stage=stage,
                name=name
                if name is not None
                else (
                    component_func.__name__
                    if hasattr(component_func, "__name__")
                    else (
                        component_func.__class__.__name__
                        if hasattr(component_func, "__class__")
                        else str(component_func)
                    )
                ),
                dependencies=dependencies,
            )
            try:
                self._add_component_at_position(new_component, position, reference)
            except Exception as e:
                raise ValueError(f"Error adding component: {str(e)}")

            if stage:
                if stage not in self._stages:
                    self._stages[stage] = []
                self._stages[stage].append(func)
                logger.debug(
                    f"Successfully added component '{new_component.name}' to stage '{stage}'."
                )

            return func

        if component is None:
            return wrapper
        if callable(component):
            return wrapper(component)
        else:
            raise ValueError("Component must be callable")

    def _add_component_at_position(self, new_component, position, reference):
        """
        Add a new component to the pipeline at a specified position.

        Args:
            new_component (PipelineNode): The new component to be added to the pipeline.
            position (str): The position where the component should be added.
                            Valid values are 'first', 'last', 'after', 'before', or 'default'.
            reference (str, optional): The name of the reference component when using 'after' or 'before' positions.

        Raises:
            ValueError: If an invalid position is provided or if a reference is required but not provided.

        This method handles the insertion of a new component into the pipeline based on the specified position:
        - 'first': Inserts the component at the beginning of the pipeline.
        - 'last' or 'default': Appends the component to the end of the pipeline.
        - 'after' or 'before': Inserts the component relative to a reference component.

        For 'after' and 'before' positions, a reference component name must be provided.
        """
        if position == "first":
            self._components.insert(0, new_component)
        elif position in ["last", "default"]:
            self._components.append(new_component)
        elif position in ["after", "before"]:
            if not reference:
                raise ValueError(
                    f"Reference must be provided for position '{position}'."
                )
            offset = 1 if position == "after" else 0
            self._insert_relative_position(new_component, reference, offset)
        else:
            raise ValueError(
                f"Invalid position '{position}'. Must be 'first', 'last', 'after', 'before', or 'default'."
            )

    def _insert_relative_position(self, component, reference, offset):
        """
        Insert a component relative to a reference component in the pipeline.

        Args:
            component (PipelineNode): The component to be inserted.
            reference (str): The name of the reference component.
            offset (int): The offset from the reference component (0 for before, 1 for after).

        Raises:
            ValueError: If the reference component is not found in the pipeline.
        """
        ref_index = next(
            (i for i, c in enumerate(self._components) if c.name == reference), None
        )
        if ref_index is None:
            raise ValueError(f"Reference component '{reference}' not found.")

        self._components.insert(ref_index + offset, component)

    def remove(self, component_name: str) -> None:
        """
        Removes a component from the pipeline.

        Args:
            component_name (str): The name of the component to be removed.

        Raises:
            ValueError: If the component is not found in the pipeline.

        Returns:
            None

        Logs:
            DEBUG: When the component is successfully removed.
            WARNING: If the component fails to be removed after attempting to do so.
        """
        # Check if the component exists in the pipeline
        if not any(c.name == component_name for c in self._components):
            raise ValueError(f"Component '{component_name}' not found in the pipeline.")

        # Remove the component from self.components
        original_count = len(self._components)
        self._components = [c for c in self._components if c.name != component_name]

        # Remove the component from stages
        for stage in self._stages.values():
            stage[:] = [c for c in stage if c.__name__ != component_name]

        # Validate that the component was removed
        if len(self._components) == original_count or any(
            c.__name__ == component_name
            for stage in self._stages.values()
            for c in stage
        ):
            logger.warning(
                f"Failed to remove component '{component_name}' from the pipeline."
            )
        logger.debug(
            f"Successfully removed component '{component_name}' from the pipeline."
        )

    def replace(
        self,
        old_component_name: str,
        new_component: Union[
            BaseComponent[T], Callable[[DataContainer[T]], DataContainer[T]]
        ],
    ) -> None:
        """
        Replaces a component in the pipeline with a new component.

        Args:
            old_component_name (str): The name of the component to be replaced.
            new_component (Union[BaseComponent[T], Callable[[DataContainer[T]], DataContainer[T]]]):
                The new component to replace the old component with.

        Returns:
            None

        Raises:
            ValueError: If the old component is not found in the pipeline.
            ValueError: If the new component is not a BaseComponent or a callable.
            ValueError: If the new component callable doesn't have the correct signature.

        Logs:
            DEBUG: When the component is successfully replaced.
        """

        if isinstance(new_component, BaseComponent):
            # It's a valid BaseComponent, no further checks needed
            pass
        elif callable(new_component):
            sig = signature(new_component)
            param = list(sig.parameters.values())[0]
            if len(sig.parameters) != 1 or not issubclass(
                param.annotation, DataContainer
            ):
                raise ValueError(
                    "New component callable must accept a single argument that is a subclass of DataContainer."
                )
        else:
            raise ValueError("New component must be a BaseComponent or a callable.")

        old_component_found = False

        # Replace in self.components
        for i, c in enumerate(self._components):
            if c.name == old_component_name:
                self._components[i] = PipelineNode(
                    func=new_component,
                    name=old_component_name,
                    position=c.position,
                    reference=c.reference,
                    stage=c.stage,
                    dependencies=c.dependencies,
                )
                old_component_found = True

        # Replace in self.stages
        for stage in self._stages.values():
            for i, c in enumerate(stage):
                if getattr(c, "name", c.__name__) == old_component_name:
                    stage[i] = new_component
                    old_component_found = True

        if not old_component_found:
            raise ValueError(
                f"Component '{old_component_name}' not found in the pipeline."
            )
        else:
            logger.debug(
                f"Successfully replaced component '{old_component_name}' in the pipeline."
            )

    def __call__(self, data: Union[T, DataContainer[T]]) -> DataContainer[T]:
        if self._built_pipeline is None:
            self._built_pipeline = self.build()
        return self._built_pipeline(data)

    def build(self) -> Callable:
        """
        Builds and returns a pipeline function that applies a series of components to the input data.
        Returns:
            pipeline: A function that takes input data and applies the ordered components to it.
        Raises:
            ValueError: If a circular dependency is detected among the components.
        """

        def resolve_dependencies():
            resolved = []
            unresolved = self._components.copy()

            while unresolved:
                for component in unresolved:
                    if all(
                        dep in [c.name for c in resolved]
                        for dep in component.dependencies
                    ):
                        resolved.append(component)
                        unresolved.remove(component)
                        break
                else:
                    raise ValueError("Circular dependency detected")

            return [c.func for c in resolved]

        ordered_components = resolve_dependencies()

        def pipeline(data: Union[T, DataContainer[T]]) -> DataContainer[T]:
            if self._input_connector:
                data = self._input_connector.input(data)

            if not isinstance(data, DataContainer):
                data = DataContainer(data)

            data = reduce(lambda d, comp: comp(d), ordered_components, data)
            if self._output_connector:
                data = self._output_connector.output(data)

            return data

        if self._built_pipeline is not pipeline:
            self._built_pipeline = pipeline

        return pipeline


class Pipeline(BasePipeline, Generic[T]):
    """
    Default Pipeline class for creating a basic data processing pipeline.
    This class inherits from BasePipeline and provides a default implementation
    of the configure_pipeline method, which does not add any specific components.
    """

    def configure_pipeline(self, model_path: str) -> None:
        """
        Configures the pipeline by adding components based on the provided model path.
        This default implementation does not add any specific components.

        Args:
            model_path (str): The path to the model used for configuring the pipeline.
        """
        # Default implementation: No specific components added
        pass
