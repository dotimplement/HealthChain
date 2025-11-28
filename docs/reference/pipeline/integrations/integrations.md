# NLP Integrations

This document provides an overview of the integration components available in the HealthChain package. These components allow you to easily incorporate popular NLP libraries into your HealthChain pipelines.

## Table of Contents

1. [SpacyNLP](#spacynlp)
2. [HFTransformer](#hftransformer)
3. [LangChainLLM](#langchainllm)

## Installation Requirements
Before utilizing the integration components, it is important to note that the required third-party libraries are not included in HealthChain's default installation. This design decision was made to:

- Maintain a lean and flexible core package
- Allow users to selectively install only the necessary dependencies
- Avoid potential version conflicts with other packages in your environment

To use these integrations, you will need to manually install the corresponding libraries using `pip`.

```python
pip install spacy
python -m spacy download en_core_web_sm  # or another desired model
pip install transformers
pip install langchain
```


## SpacyNLP

The `SpacyNLP` component allows you to integrate spaCy models into your HealthChain pipeline. There are two ways to initialize this component:

1. Using a pre-configured spaCy `Language` object:
   ```python
   import spacy
   from healthchain.pipeline.components.integrations import SpacyNLP

   nlp = spacy.load("en_core_web_sm")
   spacy_component = SpacyNLP(nlp)
   ```

2. Using the factory method with a model identifier or path to a custom local model:
   ```python
   from healthchain.pipeline.components.integrations import SpacyNLP

   # Using a standard spaCy model
   spacy_component = SpacyNLP.from_model_id(
      "en_core_web_sm",
      disable=["parser"]  # kwargs passed to spacy.load()
   )

   # Using a custom local model
   spacy_component = SpacyNLP.from_model_id("/path/to/your/model")
   ```


Choose the appropriate model based on your specific needs - standard models for general text, custom-trained models for domain-specific tasks, or specialized models like [scispaCy](https://allenai.github.io/scispacy/) for biomedical text analysis.

```python
# Using scispaCy models for biomedical text (requires: pip install scispacy)
spacy_component = SpacyNLP.from_model_id("en_core_sci_sm")
```

The component will process documents using spaCy and store the spaCy Doc object in the document's `nlp` annotations. It can be accessed using the `Document.nlp.get_spacy_doc()` method.

### Example

```python
from healthchain.io.containers import Document
from healthchain.pipeline.base import Pipeline
from healthchain.pipeline.components.integrations import SpacyNLP

pipeline = Pipeline()
pipeline.add_node(SpacyNLP.from_model_id("en_core_web_sm"))

doc = Document("This is a test sentence.")
processed_doc = pipeline(doc)

# Access spaCy annotations
spacy_doc = processed_doc.nlp.get_spacy_doc()
for token in spacy_doc:
    print(f"Token: {token.text}, POS: {token.pos_}, Lemma: {token.lemma_}")
```

## HFTransformer

The `HFTransformer` integrates HuggingFace `transformers` models into your HealthChain pipeline. Models can be browsed on the [HuggingFace website](https://huggingface.co/models).

HuggingFace offers models for a wide range of different tasks, and while not all of these have been thoroughly tested for HealthChain compatibility, we expect that all NLP models and tasks should be compatible. If you have an issues integrating any models please raise an issue on our [Github homepage](https://github.com/dotimplement/HealthChain)!

There are two ways to initialize this component:

1. Using a pre-configured HuggingFace pipeline:
   ```python
   from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
   from healthchain.pipeline.components.integrations import HFTransformer

   model_id = "gpt2"
   tokenizer = AutoTokenizer.from_pretrained(model_id)
   model = AutoModelForCausalLM.from_pretrained(model_id)
   pipe = pipeline(
      "text-generation",
      model=model,
      tokenizer=tokenizer,
      max_new_tokens=10
   )

   huggingface_component = HFTransformer(pipe)
   ```

2. Using the factory method with a model identifier:
   ```python
   from healthchain.pipeline.components.integrations import HFTransformer

   huggingface_component = HFTransformer.from_model_id(
       model="facebook/bart-large-cnn",
       task="summarization",
       max_length=130,  # kwargs passed to pipeline()
       min_length=30,
       do_sample=False
   )
   ```

The factory method requires the following arguments:

- `task` (str): The NLP task to perform (e.g., "sentiment-analysis", "named-entity-recognition").
- `model` (str): The name or path of the Hugging Face model to use.
- `**kwargs**`: Additional keyword arguments passed to the `pipeline()` function.

This component applies the specified Hugging Face model to the input document and stores the output in the HealthChain `Document.models`.

It can be accessed using the `Document.models.get_output()` method with the key `"huggingface"` and the task name.

### Example

```python
from healthchain.io.containers import Document
from healthchain.pipeline.base import Pipeline
from healthchain.pipeline.components.integrations import HFTransformer

pipeline = Pipeline()
pipeline.add_node(HFTransformer.from_model_id(
   task="sentiment-analysis",
   model="distilbert-base-uncased-finetuned-sst-2-english"
   )
)

doc = Document("I love using HealthChain for my NLP projects!")
processed_doc = pipeline(doc)

# Access Hugging Face output
sentiment_result = processed_doc.models.get_output(
   "huggingface", "sentiment-analysis"
)

print(f"Sentiment: {sentiment_result}")
```

## LangChainLLM

The `LangChainLLM` allows you to integrate LangChain chains into your HealthChain pipeline.

```python
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.llms import FakeListLLM

from healthchain.pipeline.components.integrations import LangChainLLM

# Let's create a simple FakeListLLM for demonstration
fake_llm = FakeListLLM(responses=["This is a great summary!"])

# Define the prompt template
prompt = PromptTemplate.from_template("Summarize the following text: {text}")

# Create the LCEL chain
chain = prompt | fake_llm | StrOutputParser()

# Create the component
langchain_component = LangChainLLM(
    chain=chain,
    task="chat",
    temperature=0.7  # Optional kwargs passed to invoke()
)
```

The component requires the following arguments:

- `chain`: A LangChain chain object to be executed within the pipeline.
- `task`: The key to store the output in `Document.models`.
- `**kwargs**`: Additional keyword arguments passed to the `invoke()` method.

This component runs the specified LangChain chain on the input document's text and stores the output in the HealthChain `Document.models`.

It can be accessed using the `Document.models.get_output()` method with the key `"langchain"` and the task name.


### Example

```python
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.llms import FakeListLLM

from healthchain.io.containers import Document
from healthchain.pipeline.base import Pipeline
from healthchain.pipeline.components.integrations import LangChainLLM

# Set up LangChain with a FakeListLLM
fake_llm = FakeListLLM(
    responses=["HealthChain integrates NLP libraries for easy pipeline creation."]
)
# Define the prompt template
prompt = PromptTemplate.from_template("Summarize the following text: {text}")

# Create the LCEL chain
chain = prompt | fake_llm | StrOutputParser()

# Set up your HealthChain pipeline
pipeline = Pipeline()
pipeline.add_node(LangChainLLM(chain=chain, task="summarization"))

# Let's summarize something
doc = Document(
    "HealthChain is a powerful package for building NLP pipelines. It integrates seamlessly with popular libraries like spaCy, Hugging Face Transformers, and LangChain, allowing users to create complex NLP workflows with ease."
)
processed_doc = pipeline(doc)

# What summary did we get?
summary = processed_doc.models.get_output("langchain", "summarization")
print(f"Summary: {summary}")

```

## Combining Components

You can easily combine multiple integration components in a single HealthChain pipeline:

```python
from healthchain.io.containers import Document
from healthchain.pipeline.base import Pipeline
from healthchain.pipeline.components.integrations import (
    SpacyNLP,
    HFTransformer,
    LangChainLLM,
)

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.llms import FakeListLLM

# Set up our components
spacy_component = SpacyNLP.from_model_id("en_core_web_sm")
huggingface_component = HFTransformer.from_model_id(
    model="distilbert-base-uncased-finetuned-sst-2-english",
    task="sentiment-analysis",
)

# Set up LangChain with a FakeListLLM
fake_llm = FakeListLLM(responses=["HealthChain: Powerful NLP pipeline builder."])
# Define the prompt template
prompt = PromptTemplate.from_template("Summarize the following text: {text}")
# Create the LCEL chain
chain = prompt | fake_llm | StrOutputParser()
langchain_component = LangChainLLM(chain=chain, task="summarization")

# Build our pipeline
pipeline = Pipeline()
pipeline.add_node(spacy_component)
pipeline.add_node(huggingface_component)
pipeline.add_node(langchain_component)
pipeline.build()

# Process a document
doc = Document("HealthChain makes it easy to build powerful NLP pipelines!")
processed_doc = pipeline(doc)

# Let's see what we got!
spacy_doc = processed_doc.nlp.get_spacy_doc()
sentiment = processed_doc.models.get_output("huggingface", "sentiment-analysis")
summary = processed_doc.models.get_output("langchain", "summarization")

print(f"Tokens: {[token.text for token in spacy_doc]}")
print(f"Sentiment: {sentiment}")
print(f"Summary: {summary}")


```

This documentation provides an overview of the integration components available in HealthChain. For more detailed information on each library, please refer to their respective documentation:

- [spaCy Documentation](https://spacy.io/api)
- [Hugging Face Transformers Documentation](https://huggingface.co/transformers/)
- [LangChain Documentation](https://python.langchain.com/docs/introduction/)
