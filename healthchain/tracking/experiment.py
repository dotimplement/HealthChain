from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, List, Set
from enum import Enum
import uuid
from pathlib import Path
import json


class ExperimentStatus(Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ComponentMetadata:
    name: str
    type: str
    stage: str
    config: Dict[str, Any]
    input_nodes: Set[str]
    output_nodes: Set[str]


@dataclass
class PipelineMetadata:
    name: str
    components: Dict[str, ComponentMetadata]
    input_components: List[str]
    output_components: List[str]
    stages: List[str]


@dataclass
class ExperimentMetadata:
    id: str
    name: str
    start_time: datetime
    end_time: Optional[datetime]
    status: ExperimentStatus
    sandbox_class: Optional[str]
    workflow: Optional[str]
    pipeline: Optional[PipelineMetadata]
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    tags: Dict[str, str]


class ExperimentTracker:
    def __init__(
        self,
        storage_uri: str = "./output/experiments",
        project_name: str = "healthchain",
    ):
        self.storage_uri = Path(storage_uri)
        self.storage_uri.mkdir(parents=True, exist_ok=True)
        self.project_name = project_name
        self.current_experiment: Optional[ExperimentMetadata] = None

    def start_experiment(
        self, name: str, pipeline=None, tags: Dict[str, str] = None
    ) -> str:
        experiment_id = str(uuid.uuid4())

        pipeline_metadata = None
        if pipeline is not None:
            pipeline_metadata = self._extract_pipeline_metadata(pipeline)

        self.current_experiment = ExperimentMetadata(
            id=experiment_id,
            name=name,
            start_time=datetime.now(),
            end_time=None,
            status=ExperimentStatus.RUNNING,
            sandbox_class=None,
            workflow=None,
            pipeline=pipeline_metadata,
            input_schema={},
            output_schema={},
            tags=tags or {},
        )
        return experiment_id

    def log_input(self, data: Any):
        if self.current_experiment:
            schema = self._extract_schema(data)
            self.current_experiment.input_schema["input"] = schema

    def log_output(self, data: Any):
        if self.current_experiment:
            schema = self._extract_schema(data)
            self.current_experiment.output_schema["output"] = schema

    def end_experiment(self, status: ExperimentStatus):
        if self.current_experiment:
            self.current_experiment.end_time = datetime.now()
            self.current_experiment.status = status
            self._save_experiment()

    def _extract_schema(self, data: Any) -> Dict[str, Any]:
        if hasattr(data, "model_dump"):
            return data.model_dump()
        elif hasattr(data, "__dict__"):
            return {
                "type": data.__class__.__name__,
                "attributes": list(data.__dict__.keys()),
            }
        return {"type": str(type(data))}

    def _extract_pipeline_metadata(self, pipeline) -> PipelineMetadata:
        components = {}
        for name, component in pipeline.__dict__.items():
            if not name.startswith("_"):
                config = {}
                if hasattr(component, "get_config"):
                    config = component.get_config()
                elif hasattr(component, "__dict__"):
                    config = {
                        k: v
                        for k, v in component.__dict__.items()
                        if not k.startswith("_")
                    }

                components[name] = ComponentMetadata(
                    name=component.__class__.__name__,
                    type=f"{component.__class__.__module__}.{component.__class__.__name__}",
                    stage="unknown",
                    config=config,
                    input_nodes=set(),
                    output_nodes=set(),
                )

        return PipelineMetadata(
            name=pipeline.__class__.__name__,
            components=components,
            input_components=[],
            output_components=[],
            stages=[],
        )

    def _save_experiment(self):
        if self.current_experiment:
            experiment_file = self.storage_uri / f"{self.current_experiment.id}.json"
            with open(experiment_file, "w") as f:
                # Convert experiment metadata to dict, handling datetime
                exp_dict = {
                    "id": self.current_experiment.id,
                    "name": self.current_experiment.name,
                    "start_time": self.current_experiment.start_time.isoformat(),
                    "end_time": self.current_experiment.end_time.isoformat()
                    if self.current_experiment.end_time
                    else None,
                    "status": self.current_experiment.status.value,
                    "sandbox_class": self.current_experiment.sandbox_class,
                    "workflow": self.current_experiment.workflow,
                    "input_schema": self.current_experiment.input_schema,
                    "output_schema": self.current_experiment.output_schema,
                    "tags": self.current_experiment.tags,
                }
                json.dump(exp_dict, f, indent=2)
