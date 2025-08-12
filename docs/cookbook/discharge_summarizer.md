# Build a CDS Hooks Service for Discharge Summarization

This tutorial shows you how to build a CDS service that integrates with EHR systems. We'll automatically summarize discharge notes and return actionable recommendations using the [CDS Hooks standard](https://cds-hooks.org/).

Check out the full working example [here](https://github.com/dotimplement/HealthChain/tree/main/cookbook/cds_discharge_summarizer_hf_chat.py)!

## Setup

Make sure you have a [Hugging Face API token](https://huggingface.co/docs/hub/security-tokens) and set it as the `HUGGINGFACEHUB_API_TOKEN` environment variable.

```python
import getpass
import os

if not os.getenv("HUGGINGFACEHUB_API_TOKEN"):
    os.environ["HUGGINGFACEHUB_API_TOKEN"] = getpass.getpass(
      "Enter your token: "
    )
```

If you are using a chat model, make sure you have the necessary `langchain` packages installed.

```bash
pip install langchain langchain-huggingface
```

## Initialize the pipeline

First, we'll create a [summarization pipeline](../reference/pipeline/pipeline.md) with domain-specific prompting for discharge workflows. You can choose between:

- **Transformer models** fine-tuned for clinical summarization (like `google/pegasus-xsum`)
- **Large Language Models** with custom clinical prompting (like `zephyr-7b-beta`)

For LLM approaches, we'll use [LangChain](https://python.langchain.com/docs/integrations/chat/huggingface/) for better prompting.

=== "Non-chat model"
    ```python
    from healthchain.pipeline import SummarizationPipeline

    pipeline = SummarizationPipeline.from_model_id(
      "google/pegasus-xsum", source="huggingface", task="summarization"
      )
    ```


=== "Chat model"
    ```python
    from healthchain.pipeline import SummarizationPipeline

    from langchain_huggingface.llms import HuggingFaceEndpoint
    from langchain_huggingface import ChatHuggingFace
    from langchain_core.prompts import PromptTemplate
    from langchain_core.output_parsers import StrOutputParser

    hf = HuggingFaceEndpoint(
        repo_id="HuggingFaceH4/zephyr-7b-beta",
        task="text-generation",
        max_new_tokens=512,
        do_sample=False,
        repetition_penalty=1.03,
    )

    model = ChatHuggingFace(llm=hf)

    template = """
    You are a discharge planning assistant for hospital operations.
    Provide a concise, objective summary focusing on actionable items
    for care coordination, including appointments, medications, and
    follow-up instructions. Format as bullet points.\n'''{text}'''
    """
    prompt = PromptTemplate.from_template(template)

    chain = prompt | model | StrOutputParser()

    pipeline = SummarizationPipeline.load(chain, source="langchain")
    ```

The `SummarizationPipeline` automatically:

- Parses FHIR resources from CDS Hooks requests
- Extracts clinical text from discharge documents
- Formats outputs as CDS cards according to the CDS Hooks specification

## Add the CDS FHIR Adapter

The [CdsFhirAdapter](../reference/pipeline/adapters/cdsfhiradapter.md) converts between CDS Hooks requests and HealthChain's [Document](../reference/pipeline/data_container.md) format. This makes it easy to work with FHIR data in CDS workflows.

```python
from healthchain.io import CdsFhirAdapter

cds_adapter = CdsFhirAdapter()

# Parse the CDS request to a Document object
cds_adapter.parse(request)

# Format the Document object back to a CDS response
cds_adapter.format(doc)
```

What it does:

- Parses FHIR resources from CDS requests
- Extracts text from [DocumentReference](https://www.hl7.org/fhir/documentreference.html) resources
- Formats responses as CDS cards

## Set up the CDS service

Now let's create the CDS service. [HealthChainAPI](../reference/gateway/api.md) gives you discovery endpoints, validation, and docs automatically.

```python
from healthchain.gateway import HealthChainAPI, CDSHooksService
from healthchain.models import CDSRequest, CDSResponse
from healthchain.io import CdsFhirAdapter

def create_pipeline():
    """Build the discharge summarization pipeline"""
    # Configure your pipeline (using previous examples)
    return pipeline

def create_app():
    """Create the CDS Hooks application"""
    pipeline = create_pipeline()
    adapter = CdsFhirAdapter()

    # Initialize the CDS service
    cds_service = CDSHooksService()

    # Define the CDS service function
    @cds_service.hook("encounter-discharge", id="discharge-summary")
    def handle_discharge_summary(request: CDSRequest) -> CDSResponse:
        """Process discharge summaries with AI"""
        # Parse CDS request to internal Document format
        doc = adapter.parse(request)

        # Process through AI pipeline
        processed_doc = pipeline(doc)

        # Format response with CDS cards
        response = adapter.format(processed_doc)
        return response

    # Register the service with the API gateway
    app = HealthChainAPI(title="Discharge Summary CDS Service")
    app.register_service(cds_service)

    return app
```


## Test with sample clinical data

Let's test the service with some sample discharge notes using the [sandbox utility](../reference/utilities/sandbox.md) and the [CdsDataGenerator](../reference/utilities/data_generator.md):

```python
from healthchain.data_generators import CdsDataGenerator

data_generator = CdsDataGenerator()
data = data_generator.generate(
  free_text_path="data/discharge_notes.csv", column_name="text"
)
print(data.model_dump())
# {
#    "prefetch": {
#        "entry": [
#        {
#            "resource": {
#                "resourceType": "Bundle",
#                ...
#            }
#        }
#    ]
# }
```

The data generator returns a `Prefetch` object, which ensures that the data is parsed correctly by the CDS service.

## Run the complete example

Run the service with `uvicorn`:

```python
import uvicorn

app = create_app()

uvicorn.run(app)
```

## What happens when you run this

## Workflow Overview

=== "1. Service Startup"
    - **URL:** [http://localhost:8000/](http://localhost:8000/)
    - **Service discovery:** `/cds-services`
    - **CDS endpoint:** `/cds-services/discharge-summary`
    - **API docs:** `/docs`

=== "2. Request Processing"
    - Receives CDS Hooks requests from EHR systems
    - Summarizes discharge notes using AI
    - Returns CDS cards with clinical recommendations

=== "3. Example CDS Response"
    ```json
    {
      "cards": [
        {
          "summary": "Discharge Transportation",
          "indicator": "info",
          "source": {
            "label": "HealthChain Discharge Assistant"
          },
          "detail": "• Transport arranged for 11:00 HRs\n• Requires bariatric ambulance and 2 crew members\n• Confirmation number: TR-2024-001"
        },
        {
          "summary": "Medication Management",
          "indicator": "warning",
          "source": {
            "label": "HealthChain Discharge Assistant"
          },
          "detail": "• Discharge medications: Apixaban 5mg, Baclofen 20mg MR\n• New anticoagulation card prepared\n• Collection by daughter scheduled"
        }
      ]
    }
    ```
