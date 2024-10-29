# HealthChain Integrations

This document provides an overview of the integration components available in the HealthChain package. These components allow you to easily incorporate popular NLP libraries into your HealthChain pipelines.

## Table of Contents

1. [SpacyComponent](#spacycomponent)
2. [HuggingFaceComponent](#huggingfacecomponent)
3. [LangChainComponent](#langchaincomponent)

## Installation Requirements
Before utilizing the integration components, it is important to note that the required third-party libraries are not included in HealthChain's default installation. This design decision was made to:

- Maintain a lean and flexible core package
- Allow users to selectively install only the necessary dependencies
- Avoid potential version conflicts with other packages in your environment

To use these integrations, you will need to manually install the corresponding libraries using pip.

```python
pip install spacy
python -m spacy download en_core_web_sm  # or another desired model
pip install transformers
pip install langchain
```


## SpacyComponent

The `SpacyComponent` allows you to integrate spaCy models into your HealthChain pipeline. There are several ways to initialize this component with different types of spaCy models:

1. Using standard spaCy models:
   ```python
   # Using a standard spaCy model (requires: python -m spacy download en_core_web_sm)
   spacy_component = SpacyComponent("en_core_web_sm")
   ```

2. Loading custom trained pipelines from a directory:
   ```python
   # Using a custom pipeline saved to disk
   spacy_component = SpacyComponent("/path/to/your/custom/model")
   ```

3. Using specialized domain models like [scispaCy](https://allenai.github.io/scispacy/) which can be used for classifying clinical or biomedical text:
   ```python
   # Using scispaCy models for biomedical text (requires: pip install scispacy)
   spacy_component = SpacyComponent("en_core_sci_sm")
   ```

Choose the appropriate model based on your specific needs - standard models for general text, custom-trained models for domain-specific tasks, or specialized models like scispaCy for biomedical text analysis.

```python
from healthchain.pipeline.components.integrations import SpacyComponent


spacy_component = SpacyComponent(path_to_pipeline="en_core_web_sm")
```

When called on a document, this component processes the input document using the specified spaCy model and adds the resulting spaCy Doc object to the HealthChain Document.

### Example

```python
from healthchain.io.containers import Document
from healthchain.pipeline.base import Pipeline
from healthchain.pipeline.components.integrations import SpacyComponent

pipeline = Pipeline()
pipeline.add_node(SpacyComponent(path_to_pipeline="en_core_web_sm"))

doc = Document("This is a test sentence.")
processed_doc = pipeline(doc)

# Access spaCy annotations
spacy_doc = processed_doc.get_spacy_doc()
for token in spacy_doc:
    print(f"Token: {token.text}, POS: {token.pos_}, Lemma: {token.lemma_}")
```

## HuggingFaceComponent

The `HuggingFaceComponent` integrates Hugging Face Transformers models into your HealthChain pipeline.

```python
from healthchain.pipeline.components.integrations import HuggingFaceComponent

huggingface_component = HuggingFaceComponent(task="sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")
```


- `task` (str): The NLP task to perform (e.g., "sentiment-analysis", "named-entity-recognition").
- `model` (str): The name or path of the Hugging Face model to use.

This component applies the specified Hugging Face model to the input document and stores the output in the HealthChain Document's `huggingface_outputs` dictionary.

### Example

```python
from healthchain.io.containers import Document
from healthchain.pipeline.base import Pipeline
from healthchain.pipeline.components.integrations import HuggingFaceComponent

pipeline = Pipeline()
pipeline.add_node(HuggingFaceComponent(task="sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english"))

doc = Document("I love using HealthChain for my NLP projects!")
processed_doc = pipeline(doc)

# Access Hugging Face output
sentiment_result = processed_doc.get_huggingface_output("sentiment-analysis")
print(f"Sentiment: {sentiment_result}")
```

## LangChainComponent

The `LangChainComponent` allows you to integrate LangChain chains into your HealthChain pipeline.

```python
from langchain import PromptTemplate, LLMChain
from langchain_core
from langchain.llms import FakeListLLM
from langchain_core.output_parsers import StrOutputParser
from healthchain.pipeline.components.integrations import LangChainComponent

# Let's create a simple FakeListLLM for demonstration
fake_llm = FakeListLLM(responses=["This is a great summary!"])

# Define the prompt template
prompt = PromptTemplate.from_template("Summarize the following text: {text}")

# Create the LCEL chain
chain = prompt | fake_llm | StrOutputParser()

langchain_component = LangChainComponent(chain=llm_chain)
```

- `chain`: A LangChain chain object to be executed within the pipeline.

This component runs the specified LangChain chain on the input document's text and stores the output in the HealthChain Document's `langchain_outputs` dictionary.

### Example

```python
from healthchain.io.containers import Document
from healthchain.pipeline.base import Pipeline
from healthchain.pipeline.components.integrations import LangChainComponent
from langchain import PromptTemplate, LLMChain
from langchain_core.output_parsers import StrOutputParser
from langchain.llms import FakeListLLM

# Set up LangChain with a FakeListLLM
fake_llm = FakeListLLM(responses=["HealthChain integrates NLP libraries for easy pipeline creation."])
# Define the prompt template
prompt = PromptTemplate.from_template("Summarize the following text: {text}")

# Create the LCEL chain
chain = prompt | fake_llm | StrOutputParser()

# Set up your HealthChain pipeline
pipeline = Pipeline()
pipeline.add_node(LangChainComponent(chain=llm_chain))

# Let's summarize something
doc = Document("HealthChain is a powerful package for building NLP pipelines. It integrates seamlessly with popular libraries like spaCy, Hugging Face Transformers, and LangChain, allowing users to create complex NLP workflows with ease.")
processed_doc = pipeline(doc)

# What summary did we get?
summary = processed_doc.get_langchain_output("chain_output")
print(f"Summary: {summary}")
```

## Combining Components

You can easily combine multiple integration components in a single HealthChain pipeline:

```python
from healthchain.io.containers import Document
from healthchain.pipeline.base import Pipeline
from healthchain.pipeline.components.integrations import SpacyComponent, HuggingFaceComponent, LangChainComponent
from langchain import PromptTemplate, LLMChain
from langchain.llms import FakeListLLM

# Set up our components
spacy_component = SpacyComponent(path_to_pipeline="en_core_web_sm")
huggingface_component = HuggingFaceComponent(task="sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")

# Set up LangChain with a FakeListLLM
fake_llm = FakeListLLM(responses=["HealthChain: Powerful NLP pipeline builder."])
# Define the prompt template
prompt = PromptTemplate.from_template("Summarize the following text: {text}")
# Create the LCEL chain
chain = prompt | fake_llm | StrOutputParser()
langchain_component = LangChainComponent(chain=llm_chain)

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
spacy_doc = processed_doc.get_spacy_doc()
sentiment = processed_doc.get_huggingface_output("sentiment-analysis")
summary = processed_doc.get_langchain_output("chain_output")

print(f"Tokens: {[token.text for token in spacy_doc]}")
print(f"Sentiment: {sentiment}")
print(f"Summary: {summary}")
```

This documentation provides an overview of the integration components available in HealthChain. For more detailed information on each library, please refer to their respective documentation:

- [spaCy Documentation](https://spacy.io/api)
- [Hugging Face Transformers Documentation](https://huggingface.co/transformers/)
- [LangChain Documentation](https://python.langchain.com/docs/introduction/)
