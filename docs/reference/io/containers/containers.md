# Containers

The `healthchain.io.containers` module provides FHIR-native containers for healthcare data processing. These containers handle the complexities of clinical data formats while providing a clean Python interface for NLP/ML pipelines.

## Available Containers

| Container | Purpose | Use Cases |
|-----------|---------|-----------|
| [**Document**](document.md) | Clinical text + FHIR resources | Clinical notes, discharge summaries, CDS workflows |
| [**Dataset**](dataset.md) | ML-ready features from FHIR | Model training/inference, feature engineering |

## DataContainer 📦

`DataContainer` is a generic base class for storing data of any type. It provides serialization methods that other containers inherit.

```python
from healthchain.io.containers import DataContainer

# Create a DataContainer with string data
container = DataContainer("Some data")

# Convert to dictionary and JSON
data_dict = container.to_dict()
data_json = container.to_json()

# Create from dictionary or JSON
container_from_dict = DataContainer.from_dict(data_dict)
container_from_json = DataContainer.from_json(data_json)
```
