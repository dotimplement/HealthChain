# Build a CDS sandbox for encounter discharge summarization

This tutorial demonstrates how to build a clinical decision support (CDS) application that summarizes information in encounter discharge notes to streamline operational workflows using the `encounter-discharge` CDS hook workflow. We will use the `SummarizationPipeline` for the application and test it using the HealthChain sandbox server.

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

First, we'll initialize our model and pipeline. You can choose between:

- A transformer model fine-tuned for summarization (like `google/pegasus-xsum`)
- An LLM chat model (like `zephyr-7b-beta`) with custom prompting

If you are using a chat model, we recommend you initialize the pipeline with the [LangChain](https://python.langchain.com/docs/integrations/chat/huggingface/) wrapper to fully utilize the chat interface and prompting functionality.

=== "Non-chat model"
    ```python
    from healthchain.pipelines import SummarizationPipeline

    pipeline = SummarizationPipeline.from_model_id(
      "google/pegasus-xsum", source="huggingface", task="summarization"
      )
    ```


=== "Chat model"
    ```python
    from healthchain.pipelines import SummarizationPipeline

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
    Provide a concise, objective summary of the input text in
    short bullet points separated by new lines, focusing on key
    actions such as appointments and medication dispense instructions,
    without using second or third person pronouns.\n'''{text}'''
    """
    prompt = PromptTemplate.from_template(template)

    chain = prompt | model | StrOutputParser()

    pipeline = SummarizationPipeline.load(chain, source="langchain")
    ```

Loading your model into `SummarizationPipeline` will automatically handle the data parsing and text extraction. Now it's ready to use with the sandbox!

## Build the sandbox

We'll deploy our `SummarizationPipeline` as a Clinical Decision Support sandbox. We can do this by creating a class that inherits from `ClinicalDecisionSupport` and decorating it with the `@hc.sandbox` decorator.

We'll also need to implement the service method, which will process the request through our pipeline and return the result. We can define the service method with the `@hc.api` decorator.

```python
import healthchain as hc

from healthchain.use_cases import ClinicalDecisionSupport
from healthchain.models import CDSRequest, CDSResponse

@hc.sandbox
class DischargeNoteSummarizer(ClinicalDecisionSupport):
  def __init__(self):
    self.pipeline = pipeline

    @hc.api
    def my_service(self, request: CDSRequest) -> CDSResponse:
        result = self.pipeline(request)
        return result
```

## Add a data generator

Now that we have our service function defined, we'll need to generate some test data for the sandbox to send to our service. We can use the `CdsDataGenerator` to generate synthetic FHIR data for testing.

By default, the generator generates a random single patient with structured FHIR resources. To pass in free-text discharge notes for our `SummarizationPipeline`, we can set the `free_text_path` and `column_name` parameters.

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

The data generator returns a `Prefetch` object, which ensures that the data is parsed correctly inside the sandbox.

## Define client workflow

To finish our sandbox, we'll define a client function that loads the data generator into the sandbox. We'll use the `@hc.ehr` decorator and pass in the CDS hook workflow that we want to use - in this case, `encounter-discharge`. This will automatically send the generated test data to our service method when a request is made, using the workflow format that we specified.

```python
import healthchain as hc

from healthchain.use_cases import ClinicalDecisionSupport
from healthchain.models import CDSRequest, CDSResponse, Prefetch

@hc.sandbox
class DischargeNoteSummarizer(ClinicalDecisionSupport):
  def __init__(self):
    self.pipeline = pipeline
    self.data_generator = data_generator

  @hc.api
  def my_service(self, request: CDSRequest) -> CDSResponse:
    result = self.pipeline(request)
    return result

  @hc.ehr(workflow="encounter-discharge")
  def load_data_in_client(self) -> Prefetch:
    data = self.data_generator.generate_prefetch()
    return data
```

## Run the sandbox

Start the sandbox by running the `start_sandbox()` method on your class instance.

```python
summarizer = DischargeNoteSummarizer()
summarizer.start_sandbox()
```

Then run the sandbox using the HealthChain CLI:

```bash
healthchain run discharge_summarizer.py
```

The sandbox will:

- Start a FastAPI server with your service method mounted to CDS endpoints at `http://localhost:8000/`
- Generate synthetic data and send it to your service method
- Save the processed request and response to the `output/requests` and `output/responses` folders of your current working directory

An example response containing CDS cards might look like this:

```json
{
    "cards": [
        {
            "summary": "Action Item 1",
            "indicator": "info",
            "source": {
                "label": "Card Generated by HealthChain"
            },
            "detail": "- Transport arranged for 11:00 HRs, requires bariatric ambulance and 2 crew members (confirmed)."
        },
        {
            "summary": "Action Item 2",
            "indicator": "info",
            "source": {
                "label": "Card Generated by HealthChain"
            },
            "detail": "- Medication reconciliation completed, discharge medications prepared (Apixaban 5mg, Baclofen 20mg MR, new anticoagulation card) for collection by daughter"
        }
    ]
}
```
