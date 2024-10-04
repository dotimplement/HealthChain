# Data Container

The `healthchain.io.containers` module provides classes for storing and manipulating data throughout the pipeline. The main classes are `DataContainer`, `Document`, and `Tabular`.

## DataContainer

`DataContainer` is a generic base class for storing data of any type.

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

## Document

The `Document` class is used to store and manipulate text data. It extends `DataContainer` and provides additional functionality for working with text, including integration with spaCy.

```python
from healthchain.io.containers import Document

doc = Document("OpenAI released GPT-4 in 2023.")

# Basic text operations
print(f"Char count: {doc.char_count()}")
print(f"Word count: {doc.word_count()}")

# Access tokens and entities (requires spaCy preprocessing)
print(f"Tokens: {doc.tokens}")
print(f"Entities: {doc.get_entities()}")

# Iterate over tokens
for token in doc:
    print(token)

# Get document length (word count)
print(f"Document length: {len(doc)}")
```

Note: Some features like tokenization and entity recognition require setting a spaCy Doc object using a preprocessor. [TODO]

## Tabular

The `Tabular` class is used for storing and manipulating tabular data, wrapping a pandas DataFrame.

```python
import pandas as pd
from healthchain.io.containers import Tabular

# Create a Tabular object from a DataFrame
df = pd.DataFrame({'A': [1, 2, 3], 'B': ['a', 'b', 'c']})
tabular = Tabular(df)

# Access basic information
print(f"Columns: {tabular.columns}")
print(f"Row count: {tabular.row_count()}")
print(f"Column count: {tabular.column_count()}")
print(f"Data types: {tabular.dtypes}")

# Describe the tabular data
print(tabular.describe())

# Remove a column
tabular.remove_column('A')

# Save to CSV
tabular.to_csv('output.csv')

# Create from CSV
tabular_from_csv = Tabular.from_csv('input.csv')
```

These classes provide a consistent interface for working with different types of data in the healthchain pipeline.
