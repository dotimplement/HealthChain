from dataclasses import dataclass
from enum import Enum
import json
from typing import Any, Dict, List, Optional, Set
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import uuid
import dill
from pathlib import Path

from .database import Base, Experiment, PipelineComponent


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
        storage_uri: str = "sqlite:///experiments.db",
        project_name: str = "healthchain",
    ):
        self.engine = create_engine(storage_uri)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.project_name = project_name
        self.current_experiment = None

        # Create directory for pipeline serialization
        self.pipeline_dir = Path("./output/pipelines")
        self.pipeline_dir.mkdir(parents=True, exist_ok=True)

    def start_experiment(
        self, name: str, pipeline=None, tags: Dict[str, str] = None
    ) -> str:
        experiment_id = str(uuid.uuid4())

        # Create new experiment record
        experiment = Experiment(
            id=experiment_id,
            name=name,
            start_time=datetime.now(),
            status="RUNNING",
            tags=tags or {},
            input_schema={},
            output_schema={},
        )

        # Save pipeline configuration if provided
        if pipeline is not None:
            # Save pipeline configuration
            pipeline_config = self._extract_pipeline_metadata(pipeline)
            experiment.pipeline_config = pipeline_config

            # Serialize pipeline components
            for i, component in enumerate(pipeline._components):
                pc = PipelineComponent(
                    experiment_id=experiment_id,
                    name=component.name,
                    type=component.func.__class__.__name__,
                    stage=component.stage,
                    position=i,
                )
                experiment.components.append(pc)

        # Save to database
        session = self.Session()
        session.add(experiment)
        session.commit()

        self.current_experiment = experiment
        return experiment_id

    def end_experiment(self, status: ExperimentStatus):
        if self.current_experiment:
            session = self.Session()
            experiment = session.query(Experiment).get(self.current_experiment.id)
            experiment.end_time = datetime.now()
            experiment.status = status.value
            session.commit()
            session.close()

    def load_pipeline(self, experiment_id: str):
        """Load a serialized pipeline from an experiment"""
        pipeline_path = self.pipeline_dir / f"{experiment_id}.pkl"
        if pipeline_path.exists():
            with open(pipeline_path, "rb") as f:
                return dill.load(f)
        return None

    def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        """Retrieve experiment details from database"""
        session = self.Session()
        experiment = session.query(Experiment).get(experiment_id)
        session.close()
        return experiment

    def list_experiments(self, filters: Dict[str, Any] = None) -> List[Experiment]:
        """List all experiments with optional filtering"""
        session = self.Session()
        query = session.query(Experiment)

        if filters:
            for key, value in filters.items():
                if hasattr(Experiment, key):
                    query = query.filter(getattr(Experiment, key) == value)

        experiments = query.all()
        session.close()
        return experiments

    def _extract_pipeline_metadata(self, pipeline) -> Dict[str, Any]:
        components = {}
        for name, component in pipeline.__dict__.items():
            print("#######################")
            print(name, component)
            if not name.startswith("_"):
                config = {}
                if hasattr(component, "get_config"):
                    config = component.get_config()
                elif hasattr(component, "__dict__"):
                    config = {
                        k: v
                        for k, v in component.__dict__.items()
                        if not k.startswith("_") and self._is_json_serializable(v)
                    }

                components[name] = {
                    "name": component.__class__.__name__,
                    "type": f"{component.__class__.__module__}.{component.__class__.__name__}",
                    "stage": "unknown",
                    "config": config,
                    "input_nodes": [],  # Convert set to list
                    "output_nodes": [],  # Convert set to list
                }

        return {
            "name": pipeline.__class__.__name__,
            "components": components,
            "input_components": [],
            "output_components": [],
            "stages": [],
        }

    def _is_json_serializable(self, obj):
        try:
            json.dumps(obj)
            return True
        except (TypeError, OverflowError):
            return False
