from typing import Callable, Type, Union, List, Literal, Dict, TypeVar, Generic
from functools import reduce
from pydantic import BaseModel
from dataclasses import dataclass, field

from healthchain.pipeline.container import DataContainer
from healthchain.pipeline.component import Component

T = TypeVar("T")


# TODO: dynamic resolution, maybe
PositionType = Literal["first", "last", "default", "after", "before"]


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


class Pipeline(Generic[T]):
    """
    Pipeline class for creating and managing a data processing pipeline.
    The Pipeline class allows users to create a data processing pipeline by adding components and defining their dependencies and execution order. It provides methods for adding, removing, and replacing components, as well as building and executing the pipeline.
    Attributes:
        components (List[PipelineNode]): A list of PipelineNode objects representing the components in the pipeline.
        stages (Dict[str, List[Callable]]): A dictionary mapping stage names to lists of component functions.
    """

    def __init__(self):
        self.components: List[PipelineNode[T]] = []
        self.stages: Dict[str, List[Callable]] = {}

    def __repr__(self) -> str:
        components_repr = "\n".join([repr(component) for component in self.components])
        return f"[\n{components_repr}\n]"

    def add(
        self,
        component: Union[
            Component[T], Callable[[DataContainer[T]], DataContainer[T]]
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
        Adds a component to the pipeline.

        Args:
            component (Union[Component[T], Callable[[DataContainer[T]], DataContainer[T]]], optional):
                The component to be added. It can be either a Component object or a callable function.
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
                    input_model(**data.data.__dict__)

                # Run the component
                result = func(data)

                # Validate output if output_model is provided
                if output_model:
                    output_model(**result.data.__dict__)

                return result

            component_func = (
                validated_component if input_model or output_model else func
            )
            new_component = PipelineNode(
                func=component_func,
                position=position,
                reference=reference,
                stage=stage,
                name=name or func.__name__,
                dependencies=dependencies,
            )

            if position == "first":
                self.components.insert(0, new_component)
            elif position == "last":
                self.components.append(new_component)
            elif position in ["after", "before"]:
                ref_index = next(
                    i for i, c in enumerate(self.components) if c.name == reference
                )
                insert_index = ref_index if position == "before" else ref_index + 1
                self.components.insert(insert_index, new_component)
            else:
                self.components.append(new_component)

            if stage:
                if stage not in self.stages:
                    self.stages[stage] = []
                self.stages[stage].append(func)

            return func

        if component is None:
            return wrapper
        if isinstance(component, Component):
            return wrapper(component)
        else:
            return wrapper(component)

    def remove(self, component_name: str) -> None:
        """
        Removes a component from the pipeline.

        Parameters:
        - component_name (str): The name of the component to be removed.

        Returns:
        None
        """
        self.components = [c for c in self.components if c.name != component_name]
        for stage in self.stages.values():
            stage[:] = [c for c in stage if c.__name__ != component_name]

    def replace(
        self,
        old_component_name: str,
        new_component: Union[
            Component[T], Callable[[DataContainer[T]], DataContainer[T]]
        ],
    ) -> None:
        """
        Replaces a component in the pipeline with a new component.

        Args:
            old_component_name (str): The name of the component to be replaced.
            new_component (Union[Component[T], Callable[[DataContainer[T]], DataContainer[T]]]):
                The new component to replace the old component with.

        Returns:
            None
        """
        for c in self.components:
            if c.name == old_component_name:
                c.func = new_component
                break
        for stage in self.stages.values():
            for i, c in enumerate(stage):
                if c.__name__ == old_component_name:
                    stage[i] = new_component
                    break

    def build(self) -> None:
        """
        Builds and returns a pipeline function that applies a series of components to the input data.
        Returns:
            pipeline: A function that takes input data and applies the ordered components to it.
        Raises:
            ValueError: If a circular dependency is detected among the components.
        """

        def resolve_dependencies():
            resolved = []
            unresolved = self.components.copy()

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
            if not isinstance(data, DataContainer):
                data = DataContainer(data)
            return reduce(lambda d, comp: comp(d), ordered_components, data)

        return pipeline
