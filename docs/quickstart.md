# Quickstart

## Core Components

### Sandbox
a sandbox is a standard-compliant client-to-service full pipeline environment. For a given sandbox run:

1. Data is generated or loaded into a client (EHR)

2. Data is wrapped and sent as standard-compliant API requests the designated service

3. Data is processed by the service

4. Processed result is wrapped and sent back to the service as standard-compliant API Response

5. Data is received by the client and rendered in a UI interface

To declare a sandbox, create a class that inherits from a type of `UseCase` and decorate it with the `@sandbox` decorator.

Note that **both must** be present for a valid sandbox declaration: `UseCase` loads in the blueprint of what kind of service, client, and API is set up based on HL7-specified standards, and `@sandbox` orchestrates these interactions.

```python
import healthchain as hc

from healthchain.use_cases import ClinicalDecisionSupport

@sandbox
class MyCoolSandbox(ClinicalDecisionSupport):
    def __init__(self) -> None:
        pass
```
In this example, we are giving our sandbox the name `MyCoolSandbox` and telling it to behave like a clinical decision support system (based on CDS Hooks), and declaring it should be run in a sandbox.

### Client
A client is a healthcare system object that requests information and processing from an external service.

A client is typically an EHR system, but we may also support other health objects in the future such as a CPOE (Computerized Ohysician Order Entry).

We can mark a client by using the decorator `@ehr`. You **must** declare a workflow, which informs the sandbox how your data will be formatted (See Use Cases).

You can optionally specify if you want more than 1 request generated with the `num` parameter.

```python
import healthchain as hc
from healthchain.use_cases import ClinicalDecisionSupport

@sandbox
class MyCoolSandbox(ClinicalDecisionSupport):
    def __init__(self):
        pass

    @hc.ehr(workflow="patient-view", num=10)
    def load_data_in_client(self):
        # Do things here to load in your data

```

### Service API
A service is typically an API of an external AI/NLP system that returns data to the client. Practically speaking, this is where you put the exciting stuff in, and it can be anything from a spacy pipeline to a highly sophisticated LLM agentic workflow.

When you decorate a function with `@api` in a sandbox, the function is marked as a service endpoint and will be set up as an API an EHR can make requests to.

If you are using a model that requires initialisation steps, we recommend you initialise this in your class `__init__`.

=== "HuggingFace"
    ```bash
    pip install transformers
    ```
    ```python
    import healthchain as hc
    from transformers import pipeline

    @hc.sandbox
    class MySandbox(ClinicalDecisionSupport):
        def __init__(self):
            self.pipeline = pipeline('summarization')

        @hc.api
        def my_service(self, text: str):
            results = self.pipeline(texts)
            return list(map(lambda res: res['summary_text'], results))
    ```
=== "Langchain"
    ```bash
    pip install langchain langchain_openai
    ```
    ```python
    import healthchain as hc
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import PromptTemplate
    from langchain_core.output_parsers import StrOutputParser

    @hc.sandbox
    class MySandbox(ClinicalDecisionSupport):
        def __init__(self):
            self.chain = self._init_llm_chain()

        def _init_llm_chain(self):
            prompt = PromptTemplate.from_template("Summarize the text below {text}")
            model = ChatOpenAI(model="gpt-4")
            parser = StrOutputParser()

            chain = prompt | model | parser

            return chain

        @hc.api
        def my_service(self, text: str):
            result = self.chain.invoke(text)

            return result
    ```

By default the server is created using FastAPI and you can see details of the endpoints at `/docs`.


### Data Generator
Healthcare data is interoperable, but not composable. Even though standards exist, the reality is that every deployment site or trust will have different flavours ways of configuring data and terminology.

This matters when you develop applications that need to integrate into these systems, especially when you need to reliably extract data for your AI/NLP model to consume.

The aim of the data generator in HealthChain is not to generate realistic data suitable for use cases such as patient population studies, but rather to generate data that is structurally compliant with what is expected of EHR configurations, and to be able to test and handle variations in this.

For this reason the data generator is opiniated by use case and workflow. See [Use Cases](usecases.md).

!!! note
    We're aware we may not cover everyone's use cases, so if you have strong opinions about this, please [reach out]()!

You can use the data generator within a Client function or on its own:

=== "Within client"
    ```python
    import healthchain as hc
    from healthchain.data_generator import DataGenerator

    @sandbox
    class MyCoolSandbox(ClinicalDecisionSupport):
        def __init__(self):
            self.data_generator = DataGenerator()

        @hc.ehr(workflow="patient-view")
        def load_data_in_client(self):
            self.data_generator.generate()
            return self.data_generator.data
    ```


=== "On its own"
    ```python
    from healthchain.data_generator import DataGenerator

    # Initialise data generator
    data_generator = DataGenerator()

    # Generate FHIR resources for use case workflow
    data_generate.set_workflow("patient-discharge")
    data_generator.generate()

    print(data.generator.data)
    ```

<!-- You can pass in parameters in `contraint` argument to limit the general form of the FHIR resources you get back, but this feature is experimental. Arguments supported are:
- `"has_medication_request"`
- `"has_problem_list"`
- `"has_procedures"`
- `"long_encounter_period"`

```python
data_generator.generate(constrain=["has_medication_requests"])
```
-->

#### Loading free-text

For free-text data such as discharge summaries, we also provide a method `.load_free_text()` for wrapping the text into a FHIR [DocumentReference](https://build.fhir.org/documentreference.html) resource (N.B. currently we place the text directly in the resource attachment, although it is technically supposed to be base64 encoded).

Input must be a directory of `.txt` files, where a random file will be picked for each generation.

```python
# Load free text into a DocumentResource FHIR resource
data_generator.load_free_text("./dir/to/txt/files")
```

#### Other synthetic data sources
If you are looking for more realistic patient population data, you are also free to define your own data in a sandbox run! Check out [MIMIC](https://mimic.mit.edu/) for comprehensive records and free-text data, or [Synthea](https://synthetichealth.github.io/synthea/) for synthetically generated FHIR resources. Both are open-source, although you will need to complete [PhysioNet Credentialing](https://mimic.mit.edu/docs/gettingstarted/) to access MIMIC.


## Full Example

```python
import healthchain as hc

from healthchain.use_cases import ClinicalDecisionSupport
from healthchain.data_generator import DataGenerator

@sandbox
class MyCoolSandbox(ClinicalDecisionSupport):
    def __init__(self):
        self.data_generator = DataGenerator()
    
    @hc.ehr(workflow="encounter-discharge", num=10)
    def load_data_in_client(self):
        self.data_generator.generate()
        return self.data_generator.data
    
    @hc.api
    def llm_server(self, text: str):
        return {
            "cards": [
                {
                    "summary": "This will be generated by your model",
                    "indicator": "info",
                    "source": {"label": "resource"},
                }
            ]
        }


if __name__ == "__main__":
    cds = MyCoolSandbox()
    cds.start_sandbox()

```


## Deploy sandbox locally with FastAPI 🚀

To run your sandbox:

```bash
healthchain my_sandbox.py
```


## Inspect generated data in Streamlit 🎈

By default, data generated from your sandbox runs is saved at `./output/`. The streamlit dashboard is run separately and will assume this is where your data is saved. 

To run the streamlit app:

```bash
streamlit streamlit_app/app.py
```
