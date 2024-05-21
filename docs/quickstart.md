# Quickstart

## Core Components

### Sandbox
a sandbox is a standard-compliant client-to-service full pipeline environment. For a given sandbox run:
1.  Data is generated or loaded into a client (EHR)
2. Data is wrapped and sent as standard-compliant API requests the designated service
3. Data is processed by the service
4. Processed result is wrapped and sent back to the service as standard-compliant API Response
5. Data is received by the client and rendered in a UI interface


### Client
A client is a healthcare system object that requests information and processing from an external service.

A client is typically an Electronic Health Record (EHR) system, but we may also support other health objects in the future such as a CPOE (Computerized Ohysician Order Entry)

### Service API
A service is typically an API of an external AI/NLP system that returns data to the client. Practically speaking, this is where you put your cool stuff in, and it can be anything from a spacy pipeline to a highly sophisticated LLM agentic workflow.

When you decorate a function with `@api` in a sandbox, the function is marked as a service endpoint and will be mounted at the appropriate endpoint that an EHR will call upon.

If you are using a model or LLM chain, we recommend you initialise this first.

```python
import healthchain as hc

@hc.sandbox
class MySandbox(UseCase):
    def __init__(self):
        self.chain = self._init_llm_chain()

    def _init_llm_chain(self):
        prompt = """Extract some information from the following data"""
        llm = OpenAI()
        parser = JsonOutputParser()

        chain = prompt | llm | parser

        return chain

    @hc.api
    def my_service(self, text: str):
        result = self.chain.invoke(text)
        return result
```

### Data Generator
Healthcare data is interoperable, but not composable. Even though standards exist, the reality is that every deployment site or trust will have different flavours and combinations of terminology sets and ways of configuring FHIR and CDA data.

This matters when you develop applications that need to integrate into these systems, especially when you need to reliably extract data for your AI/NLP model to consume. The process is often slow and manual, requiring communication across multiple teams.

The aim of the data generator in HealthChain is not to generate realistic data suitable for use cases such as patient population studies, but rather to generate data that is structurally compliant with what is expected of EHR configurations, and to be able to test and handle variations in this.

For this reason the data generator is opiniated by use case and workflow. See [Use Cases](#use-cases). We're aware we may not cover everyone's use cases, so if you have strong opinions about this, please [reach out]()!

You can use the data generator within a Client function or on its own:

```python
from healthchain.data_generator import DataGenerator

data_generator = DataGenerator()
# Generate FHIR resources for use case workflow
data_generate.set_workflow("patient-discharge")
data_generator.generate()

print(data.generator.data)
```

You can pass in parameters in `contraint` argument to limit the general form of the FHIR resources you get back, but this feature is experimental. Arguments supported are:
- `"has_medication_request"`
- `"has_problem_list"`
- `"has_procedures"`
- `"long_encounter_period"`

```python
data_generator.generate(constrain=["has_medication_requests"])
```

For free-text data such as discharge summaries, we also provide a method `.load_free_text()` for wrapping the text into a FHIR [DocumentReference](https://build.fhir.org/documentreference.html) resource (N.B. currently we place the text directly in the resource attachment, although it is technically supposed to be base64 encoded.)

```python
# Load free text into a DocumentResource FHIR resource
data_generator.load_free_text("./dir/to/txt/files")
```

If you are looking for more realistic patient population data, you are also free to define your own data in a sandbox run! Check out [MIMIC](https://mimic.mit.edu/) for comprehensive records and free-text data, or [Synthea](https://synthetichealth.github.io/synthea/) for synthetically generated FHIR resources. Both are open-source, although you will need to complete [PhysioNet Credentialing](https://mimic.mit.edu/docs/gettingstarted/) to access MIMIC.
