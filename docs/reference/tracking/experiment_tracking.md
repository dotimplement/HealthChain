# ExperimentTracker Documentation

ExperimentTracker is a simple yet powerful tool for tracking your machine learning experiments. It automatically records experiment metadata, timing, and status with minimal configuration required.

## Quick Start

The easiest way to use ExperimentTracker is through the `@sandbox` decorator:

```python
from healthchain import sandbox

@sandbox(
    experiment_config={
        "storage_uri": "sqlite:///experiments.db",  # Where to store experiment data
        "project_name": "my_project",  # Name for grouping experiments
        "tags" : {"environment": "production"}  # Optional tags
    }
)
class MyExperiment(BaseUseCase):
    def __init__(self):
        # ExperimentTracker is automatically initialized
        # You can access it via self.experiment_tracker
        pass
```

That's it! The system will automatically:
- Create a unique ID for each experiment run
- Track when experiments start and end
- Record the status (completed or failed)
- Save any tags you provide

## Viewing Your Experiments

### Database Schema

ExperimentTracker uses SQLAlchemy to store experiment data in two tables:

**experiments**:
- `id`: Unique identifier (UUID)
- `name`: Experiment name
- `start_time`: Start timestamp
- `end_time`: End timestamp
- `status`: Current status (RUNNING, COMPLETED, FAILED)
- `tags`: JSON field for custom tags
- `pipeline_config`: JSON field for pipeline configuration (optional)

**pipeline_components**:
- `id`: Component ID
- `experiment_id`: Reference to parent experiment
- `name`: Component name
- `type`: Component type
- `stage`: Processing stage
- `position`: Order in pipeline

### Using Python API

```python
# Get details for a specific experiment
experiment = tracker.get_experiment(experiment_id)
print(f"Status: {experiment.status}")
print(f"Duration: {experiment.end_time - experiment.start_time}")

# List all experiments
experiments = tracker.list_experiments()

# Filter experiments by tags
prod_experiments = tracker.list_experiments(
    filters={"tags": {"environment": "production"}}
)
```

### Querying the Database Directly

The experiment data is stored in a local SQLite database that you can query directly in a python script or Jupyter notebook:

```python
import sqlite3

# Connect to the database
conn = sqlite3.connect('experiments.db')
cursor = conn.cursor()

# View recent experiments
cursor.execute("""
    SELECT id, name, start_time, status, tags
    FROM experiments
    ORDER BY start_time DESC
    LIMIT 5;
""")
recent_experiments = cursor.fetchall()

# View experiments with a specific tag
cursor.execute("""
    SELECT id, name, start_time, status
    FROM experiments
    WHERE json_extract(tags, '$.environment') = 'production';
""")
prod_experiments = cursor.fetchall()

# Get component details for an experiment
cursor.execute("""
    SELECT name, type, stage
    FROM pipeline_components
    WHERE experiment_id = ?;
""", (experiment_id,))
components = cursor.fetchall()

conn.close()
```



## Configuration Options

The `experiment_config` dictionary supports two options:
- `storage_uri`: Where to store experiment data (default: "sqlite:///experiments.db")
  - Use SQLite: "sqlite:///experiments.db"
- `project_name`: Name for grouping related experiments (default: "healthchain")

## Example: Real-World Usage

Here's a complete example showing how ExperimentTracker is used in practice:

```python
import healthchain as hc

from healthchain.pipeline import SummarizationPipeline
from healthchain.use_cases import ClinicalDecisionSupport
from healthchain.models import CdsFhirData, CDSRequest, CDSResponse
from healthchain.data_generators import CdsDataGenerator

from langchain_huggingface.llms import HuggingFaceEndpoint
from langchain_huggingface import ChatHuggingFace

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

import getpass
import os


if not os.getenv("HUGGINGFACEHUB_API_TOKEN"):
    os.environ["HUGGINGFACEHUB_API_TOKEN"] = getpass.getpass("Enter your token: ")


@hc.sandbox(
    experiment_config={
        "storage_uri": "sqlite:///experiments.db",  # Where to store experiment data
        "project_name": "patient_summary",  # Name for grouping experiments
    }
)
class DischargeNoteSummarizer(ClinicalDecisionSupport):
    def __init__(self):
        # Initialize pipeline and data generator
        chain = self._init_chain()
        self.pipeline = SummarizationPipeline.load(
            chain, source="langchain", template_path="templates/cds_card_template.json"
        )
        self.data_generator = CdsDataGenerator()

    def _init_chain(self):
        hf = HuggingFaceEndpoint(
            repo_id="HuggingFaceH4/zephyr-7b-beta",
            task="text-generation",
            max_new_tokens=512,
            do_sample=False,
            repetition_penalty=1.03,
        )
        model = ChatHuggingFace(llm=hf)
        template = """
        You are a bed planner for a hospital. Provide a concise, objective summary of the input text in short bullet points separated by new lines,
        focusing on key actions such as appointments and medication dispense instructions, without using second or third person pronouns.\n'''{text}'''
        """
        prompt = PromptTemplate.from_template(template)
        chain = prompt | model | StrOutputParser()

        return chain

    @hc.ehr(workflow="encounter-discharge")
    def load_data_in_client(self) -> CdsFhirData:
        # Generate synthetic FHIR data for testing
        data = self.data_generator.generate(
            free_text_path="data/discharge_notes.csv", column_name="text"
        )
        return data

    @hc.api
    def my_service(self, request: CDSRequest) -> CDSResponse:
        # Process the request through our pipeline
        result = self.pipeline(request)
        return result


if __name__ == "__main__":
    # Start the sandbox server
    summarizer = DischargeNoteSummarizer()
    summarizer.start_sandbox()
```


### Performance Considerations

- SQLite (default) works well for single-user scenarios
- Large-scale deployments may want to implement custom storage backends
