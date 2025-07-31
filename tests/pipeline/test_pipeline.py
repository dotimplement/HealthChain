import pytest
from pydantic import BaseModel, Field, ValidationError
from healthchain.pipeline.base import BaseComponent
from healthchain.io.containers import DataContainer
from healthchain.pipeline.base import Pipeline


# Mock classes and functions for testing
class MockComponent:
    def __call__(self, data):
        return data


class MockInputModel(BaseModel):
    data: int = Field(gt=0)


class MockOutputModel(BaseModel):
    data: int = Field(lt=15)


def mock_component(data: DataContainer) -> DataContainer:
    data.data += 1
    return data


# Test adding components
def test_add_component(mock_basic_pipeline):
    # Test basic component addition
    mock_basic_pipeline.add_node(mock_component, name="test_component")
    assert len(mock_basic_pipeline._components) == 1
    assert mock_basic_pipeline._components[0].name == "test_component"

    # Test adding components with positions and stages
    mock_basic_pipeline.add_node(
        mock_component, name="first", position="first", stage="preprocessing"
    )
    mock_basic_pipeline.add_node(
        mock_component, name="last", position="last", stage="other_processing"
    )
    mock_basic_pipeline.add_node(
        mock_component,
        name="second",
        position="after",
        reference="first",
        stage="other_processing",
    )
    mock_basic_pipeline.add_node(
        mock_component, name="third", position="before", reference="last"
    )

    assert len(mock_basic_pipeline._components) == 5
    assert mock_basic_pipeline._components[0].name == "first"
    assert mock_basic_pipeline._components[0].stage == "preprocessing"
    assert mock_basic_pipeline._components[1].name == "second"
    assert mock_basic_pipeline._components[1].stage == "other_processing"
    assert mock_basic_pipeline._components[2].name == "test_component"
    assert mock_basic_pipeline._components[3].name == "third"
    assert mock_basic_pipeline._components[-1].name == "last"
    assert mock_basic_pipeline._components[-1].stage == "other_processing"

    # Test adding component with invalid position
    with pytest.raises(ValueError):
        mock_basic_pipeline.add_node(mock_component, name="invalid", position="middle")

    # Test adding component with missing reference
    with pytest.raises(ValueError):
        mock_basic_pipeline.add_node(
            mock_component, name="invalid", position="after", reference="nonexistent"
        )

    # Test adding component with dependencies
    mock_basic_pipeline.add_node(mock_component, name="dep1")
    mock_basic_pipeline.add_node(mock_component, name="dep2")
    mock_basic_pipeline.add_node(
        mock_component, name="main", dependencies=["dep1", "dep2"]
    )

    assert mock_basic_pipeline._components[-1].name == "main"
    assert mock_basic_pipeline._components[-1].dependencies == ["dep1", "dep2"]

    # Test adding component with input and output models
    mock_basic_pipeline.add_node(
        mock_component,
        name="validated_component",
        input_model=MockInputModel,
        output_model=MockOutputModel,
    )
    assert len(mock_basic_pipeline._components) == 9
    assert mock_basic_pipeline._components[-1].name == "validated_component"

    # Test adding component as a decorator
    @mock_basic_pipeline.add_node(name="decorator_component", stage="processing")
    def decorator_component(data: DataContainer) -> DataContainer:
        data.data += 1
        return data

    assert len(mock_basic_pipeline._components) == 10
    assert mock_basic_pipeline._components[-1].name == "decorator_component"
    assert mock_basic_pipeline._components[-1].stage == "processing"


# Test removing and replacing components
def test_remove_and_replace_component(mock_basic_pipeline, caplog):
    mock_basic_pipeline.add_node(mock_component, name="test_component")
    mock_basic_pipeline.remove("test_component")
    assert len(mock_basic_pipeline._components) == 0

    with pytest.raises(ValueError):
        mock_basic_pipeline.remove("nonexistent_component")

    mock_basic_pipeline.add_node(mock_component, name="original")

    # Test replacing with a valid callable
    def new_component(data: DataContainer) -> DataContainer:
        return data

    mock_basic_pipeline.replace("original", new_component)
    assert mock_basic_pipeline._components[0].func == new_component

    # Test replacing with an invalid callable (wrong signature)
    def invalid_component(data):
        return data

    with pytest.raises(ValueError):
        mock_basic_pipeline.replace("original", invalid_component)

    # Test replacing with a BaseComponent
    class NewComponent(BaseComponent):
        def __call__(self, data: DataContainer) -> DataContainer:
            return data

    new_base_component = NewComponent()
    mock_basic_pipeline.replace("original", new_base_component)
    assert mock_basic_pipeline._components[0].func == new_base_component

    # Test replacing a non-existent component
    with pytest.raises(ValueError):
        mock_basic_pipeline.replace("non_existent", new_component)

    # Test replacing with an invalid type
    with pytest.raises(ValueError):
        mock_basic_pipeline.replace("original", "not a component")


# Test building and executing pipeline
def test_build_and_execute_pipeline(mock_basic_pipeline):
    mock_basic_pipeline.add_node(mock_component, name="comp1")
    mock_basic_pipeline.add_node(mock_component, name="comp2")

    # Test that the pipeline automatically builds on first use
    input_data = DataContainer(1)
    result = mock_basic_pipeline(input_data)  # This should trigger the automatic build

    assert result.data == 3
    assert (
        mock_basic_pipeline._built_pipeline is not None
    )  # Check that the pipeline was built

    # Test that subsequent calls use the already built pipeline
    result2 = mock_basic_pipeline(DataContainer(2))
    assert result2.data == 4

    # Test explicit build method
    mock_basic_pipeline._built_pipeline = None  # Reset the built pipeline
    explicit_pipeline = mock_basic_pipeline.build()
    assert callable(explicit_pipeline)

    result3 = explicit_pipeline(DataContainer(3))
    assert result3.data == 5
    assert mock_basic_pipeline._built_pipeline is explicit_pipeline

    # Test circular dependency detection
    mock_basic_pipeline.add_node(mock_component, name="comp3", dependencies=["comp4"])
    mock_basic_pipeline.add_node(mock_component, name="comp4", dependencies=["comp3"])

    # Reset the built pipeline to force a rebuild
    mock_basic_pipeline._built_pipeline = None

    with pytest.raises(ValueError, match="Circular dependency detected"):
        mock_basic_pipeline(
            DataContainer(1)
        )  # This should trigger the build and raise the error

    # Also test that explicit build raises the same error
    with pytest.raises(ValueError, match="Circular dependency detected"):
        mock_basic_pipeline.build()


# Test input and output model validation
def test_input_output_validation(mock_basic_pipeline):
    def validated_component(data: DataContainer) -> DataContainer:
        data.data = data.data * 2
        return data

    mock_basic_pipeline.add_node(
        validated_component,
        name="validated",
        input_model=MockInputModel,
        output_model=MockOutputModel,
    )

    pipeline_func = mock_basic_pipeline.build()

    valid_input = DataContainer(5)
    result = pipeline_func(valid_input)
    assert result.data == 10

    invalid_input = DataContainer(-1)
    with pytest.raises(ValidationError):
        pipeline_func(invalid_input)

    # Test output validation
    @mock_basic_pipeline.add_node(
        name="invalid_output", input_model=MockInputModel, output_model=MockOutputModel
    )
    def invalid_output_component(data: DataContainer) -> DataContainer:
        data.data = data.data * 10  # This will produce an invalid output
        return data

    mock_basic_pipeline._built_pipeline = None  # Reset the built pipeline
    pipeline_func = mock_basic_pipeline.build()

    with pytest.raises(ValidationError):
        pipeline_func(DataContainer(5))  # 5 * 10 = 50, which is > 15 (invalid output)


# Test Pipeline class and representation
def test_pipeline_class_and_representation(mock_basic_pipeline):
    pipeline = Pipeline()
    assert hasattr(pipeline, "configure_pipeline")
    pipeline.configure_pipeline("dummy_path")  # Should not raise any exception

    mock_basic_pipeline.add_node(mock_component, name="comp1")
    mock_basic_pipeline.add_node(mock_component, name="comp2")

    repr_string = repr(mock_basic_pipeline)
    assert "comp1" in repr_string
    assert "comp2" in repr_string

    loaded_pipeline = Pipeline.from_local_model("dummy_path", source="spacy")
    assert isinstance(loaded_pipeline, Pipeline)


# Add a new test for the stages property
def test_stages_property(mock_basic_pipeline):
    mock_basic_pipeline.add_node(mock_component, name="comp1", stage="stage1")
    mock_basic_pipeline.add_node(mock_component, name="comp2", stage="stage2")
    mock_basic_pipeline.add_node(mock_component, name="comp3", stage="stage1")

    stages_repr = mock_basic_pipeline.stages
    assert "Pipeline Stages:" in stages_repr
    assert "stage1:" in stages_repr
    assert "stage2:" in stages_repr
    assert "- mock_component" in stages_repr

    # Test setting stages
    new_stages = {
        "new_stage1": [mock_component],
        "new_stage2": [mock_component, mock_component],
    }
    mock_basic_pipeline.stages = new_stages
    assert mock_basic_pipeline._stages == new_stages
