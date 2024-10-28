# Component

Components are the building blocks of the healthchain pipeline. They are designed to process data in a consistent manner, allowing for easy composition and reusability.


## Available Components

| Component | Description | Methods |
|-----------|-------------|---------|
| `TextPreprocessor` | Handles text preprocessing tasks | `tokenizer`: Specifies the tokenization method (e.g., `"basic"` or `"spacy"`) <br> `lowercase`: Converts text to lowercase if `True` <br> `remove_punctuation`: Removes punctuation if `True` <br> `standardize_spaces`: Standardizes spaces if `True` <br> `regex`: List of custom regex patterns and replacements |
| `Model` | Wraps machine learning and NLP models for use in the pipeline | `load_model`: Loads the specified model |
| `TextPostProcessor` | Handles text postprocessing tasks | `postcoordination_lookup`: Dictionary for entity refinement lookups |

## Creating Custom Components

You can create your own custom components by extending the `BaseComponent` class and implementing the `__call__` method.

```python
from healthchain.pipeline.base import BaseComponent

class MyCustomComponent(BaseComponent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __call__(self, data):
        # Your custom processing logic here
        return data
```
