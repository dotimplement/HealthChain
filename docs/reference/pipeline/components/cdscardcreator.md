# CdsCardCreator

More detailed documentation coming soon!

The `CdsCardCreator` is a pipeline component that creates CDS Hooks cards from either model outputs or static content. These cards can be displayed in Electronic Health Record (EHR) systems as part of clinical decision support workflows.

## Overview

The component takes text input and formats it into standardized CDS Hooks cards using `Jinja2` templates. It can create cards from:

1. Model-generated text stored in a document's model outputs container
2. Static content provided during initialization

## Usage

### Basic Usage with Model Output

```python
from healthchain.pipeline.components import CdsCardCreator

# Create cards from model output
creator = CdsCardCreator(source="huggingface", task="summarization")
doc = creator(doc)  # Creates cards from model output
```

### Using Static Content

```python
# Create cards with static content
creator = CdsCardCreator(static_content="Static card message")
doc = creator(doc)  # Creates card with static content
```

### Custom Template

```python
# Create cards with custom template
template = '''
{
    "summary": "Warning heading!",
    "indicator": "warning",
    "source": {{ default_source | tojson }},
    "detail": "{{ model_output }}"
}
'''

creator = CdsCardCreator(
    template=template,
    source="langchain",
    task="chat",
    delimiter="\n"
)
doc = creator(doc)  # Creates cards split by newlines
```

## Configuration Options

| Parameter | Type | Description |
|-----------|------|-------------|
| `template` | `str` | Optional Jinja2 template string for card creation |
| `template_path` | `str` or `Path` | Optional path to a Jinja2 template file |
| `static_content` | `str` | Optional static text to use instead of model output |
| `source` | `str` | Source framework to get model output from (e.g. "huggingface") |
| `task` | `str` | Task name to get model output from (e.g. "summarization") |
| `delimiter` | `str` | Optional string to split model output into multiple cards |
| `default_source` | `Dict[str, Any]` | Default source info for cards. Defaults to `{"label": "Card Generated by HealthChain"}` |

## Card Template Format

The default template creates an info card with the following structure:

```json
{
    "summary": "{{ model_output[:140] }}",
    "indicator": "info",
    "source": {{ default_source | tojson }},
    "detail": "{{ model_output }}"
}
```

Available template variables:
- `model_output`: The text content to display in the card
- `default_source`: Source information dictionary

## Card Properties

The created cards have the following properties:

- `summary`: Brief description (max 140 characters)
- `indicator`: Card urgency level ("info", "warning", "critical")
- `source`: Source information object
- `detail`: Full text content
- `suggestions`: Optional suggested actions
- `selectionBehavior`: Optional selection behavior
- `overrideReasons`: Optional override reasons
- `links`: Optional external links

## Error Handling

The component includes error handling for:

- Invalid template files
- Template rendering errors
- JSON parsing errors
- Missing model output

Errors are logged using the standard Python logging module.

## Integration with Pipeline

The CdsCardCreator can be used as part of a larger pipeline:

```python
from healthchain.pipeline import Pipeline
from healthchain.pipeline.components import CdsCardCreator

pipeline = Pipeline()
pipeline.add_component(CdsCardCreator(
    source="huggingface",
    task="summarization",
    template_path="path/to/template.json",
    delimiter="\n"
))
```


## Related Documentation

- [CDS Hooks Specification](https://cds-hooks.org/)
- [Clinical Decision Support Documentation](../../gateway/cdshooks.md)
