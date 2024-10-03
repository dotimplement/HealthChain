import pytest
from pydantic import BaseModel, Field, ValidationError
from healthchain.pipeline.basepipeline import BasePipeline, Pipeline, BaseComponent
from healthchain.io.containers import DataContainer


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


# Fixture for a basic pipeline
@pytest.fixture
def basic_pipeline():
    class TestPipeline(BasePipeline):
        def configure_pipeline(self, model_path: str) -> None:
            pass

    return TestPipeline()


# Test adding components
def test_add_component(basic_pipeline):
    basic_pipeline.add(mock_component, name="test_component")
    assert len(basic_pipeline._components) == 1
    assert basic_pipeline._components[0].name == "test_component"


# Test adding component with position
def test_add_component_with_position(basic_pipeline):
    basic_pipeline.add(
        mock_component, name="first", position="first", stage="preprocessing"
    )
    basic_pipeline.add(
        mock_component, name="last", position="last", stage="other_processing"
    )
    basic_pipeline.add(
        mock_component,
        name="second",
        position="after",
        reference="first",
        stage="other_processing",
    )
    basic_pipeline.add(
        mock_component, name="third", position="before", reference="last"
    )

    assert len(basic_pipeline._components) == 4
    assert basic_pipeline._components[0].name == "first"
    assert basic_pipeline._components[0].stage == "preprocessing"
    assert basic_pipeline._components[1].name == "second"
    assert basic_pipeline._components[1].stage == "other_processing"
    assert basic_pipeline._components[2].name == "third"
    assert basic_pipeline._components[-1].name == "last"
    assert basic_pipeline._components[-1].stage == "other_processing"


def test_add_component_with_invalid_position(basic_pipeline):
    with pytest.raises(ValueError):
        basic_pipeline.add(mock_component, name="invalid", position="middle")


def test_add_component_with_missing_reference(basic_pipeline):
    with pytest.raises(ValueError):
        basic_pipeline.add(
            mock_component, name="invalid", position="after", reference="nonexistent"
        )


# Test adding component with dependencies
def test_add_component_with_dependencies(basic_pipeline):
    basic_pipeline.add(mock_component, name="dep1")
    basic_pipeline.add(mock_component, name="dep2")
    basic_pipeline.add(mock_component, name="main", dependencies=["dep1", "dep2"])

    assert len(basic_pipeline._components) == 3
    assert basic_pipeline._components[-1].name == "main"
    assert basic_pipeline._components[-1].dependencies == ["dep1", "dep2"]


# Test removing component
def test_remove_component(basic_pipeline):
    basic_pipeline.add(mock_component, name="test_component")
    basic_pipeline.remove("test_component")
    assert len(basic_pipeline._components) == 0

    with pytest.raises(ValueError):
        basic_pipeline.remove("nonexistent_component")


# Test replacing component
def test_replace_component(basic_pipeline, caplog):
    basic_pipeline.add(mock_component, name="original")

    # Test replacing with a valid callable
    def new_component(data: DataContainer) -> DataContainer:
        return data

    basic_pipeline.replace("original", new_component)
    assert basic_pipeline._components[0].func == new_component

    # Test replacing with an invalid callable (wrong signature)
    def invalid_component(data):
        return data

    with pytest.raises(ValueError):
        basic_pipeline.replace("original", invalid_component)

    # Test replacing with a BaseComponent
    class NewComponent(BaseComponent):
        def __call__(self, data: DataContainer) -> DataContainer:
            return data

    new_base_component = NewComponent()
    basic_pipeline.replace("original", new_base_component)
    assert basic_pipeline._components[0].func == new_base_component

    # Test replacing a non-existent component
    with pytest.raises(ValueError):
        basic_pipeline.replace("non_existent", new_component)

    # Test replacing with an invalid type
    with pytest.raises(ValueError):
        basic_pipeline.replace("original", "not a component")


# Test building pipeline
def test_build_pipeline(basic_pipeline):
    basic_pipeline.add(mock_component, name="comp1")
    basic_pipeline.add(mock_component, name="comp2")

    pipeline_func = basic_pipeline.build()

    input_data = DataContainer(1)
    result = pipeline_func(input_data)

    assert result.data == 3


# Test circular dependency detection
def test_circular_dependency(basic_pipeline):
    basic_pipeline.add(mock_component, name="comp1", dependencies=["comp2"])
    basic_pipeline.add(mock_component, name="comp2", dependencies=["comp1"])

    with pytest.raises(ValueError, match="Circular dependency detected"):
        basic_pipeline.build()


# Test input and output model validation
def test_input_output_validation(basic_pipeline):
    def validated_component(data: DataContainer) -> DataContainer:
        data.data = data.data * 2
        return data

    basic_pipeline.add(
        validated_component,
        name="validated",
        input_model=MockInputModel,
        output_model=MockOutputModel,
    )

    pipeline_func = basic_pipeline.build()

    valid_input = DataContainer(5)
    result = pipeline_func(valid_input)
    assert result.data == 10

    invalid_input = DataContainer(-1)
    with pytest.raises(ValidationError):
        pipeline_func(invalid_input)


# Test Pipeline class
def test_pipeline_class():
    pipeline = Pipeline()
    assert hasattr(pipeline, "configure_pipeline")
    pipeline.configure_pipeline("dummy_path")  # Should not raise any exception


# Test pipeline representation
def test_pipeline_representation(basic_pipeline):
    basic_pipeline.add(mock_component, name="comp1")
    basic_pipeline.add(mock_component, name="comp2")

    repr_string = repr(basic_pipeline)
    assert "comp1" in repr_string
    assert "comp2" in repr_string


# Test loading pipeline
def test_load_pipeline():
    pipeline = Pipeline.load("dummy_path")
    assert isinstance(pipeline, Pipeline)
