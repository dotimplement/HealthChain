# Generators

Generators in the interoperability module are responsible for producing healthcare data in various formats from FHIR resources. The module includes built-in generators for common formats including CDA, HL7v2, and FHIR.

The generators are largely configuration-driven, with rendering done using Liquid templates. We highly recommend that you read through the [Templates](templates.md) and [Configuration](configuration.md) sections before using the generators!

## Available Generators

| Generator | Description |
|-----------|-------------|
| `CDAGenerator` | Generates CDA XML documents from FHIR resources |
| `FHIRGenerator` | Generates FHIR JSON/XML from FHIR resources |
<!-- | `HL7v2Generator` | Generates HL7v2 messages from FHIR resources | -->


## CDA Generator

The CDA Generator produces Clinical Document Architecture (CDA) XML documents from FHIR resources.

### Usage Examples

```python
from healthchain.interop import create_interop, FormatType
from healthchain.fhir import create_condition

# Create an engine
engine = create_interop()

# Use the FHIR helper functions to create a condition resource
condition = create_condition(
    code="38341003",
    display="Hypertension",
    system="http://snomed.info/sct",
    subject="Patient/Foo",
    clinical_status="active"
)

# Generate CDA from FHIR resources
cda_xml = engine.from_fhir([condition], dest_format=FormatType.CDA)

# Access the CDA generator directly (advanced use case)
cda_generator = engine.cda_generator
cda_xml = cda_generator.transform([condition])
```

## FHIR Generator

The FHIR Generator transforms data from other formats into FHIR resources. It currently only supports transforming CDA documents into FHIR resources.

### Usage Examples

```python
from healthchain.interop import create_interop, FormatType

# Create an engine
engine = create_interop()

# CDA section entries in dictionary format (@ is used to represent XML attributes)
cda_section_entries = {
    "problems": {
        "act": {
            "@classCode": "ACT",
            "@moodCode": "EVN"
            ...
        }
    }
}

# Generate FHIR resources
fhir_generator = engine.fhir_generator
fhir_resources = fhir_generator.transform(cda_section_entries, src_format=FormatType.CDA)
```

??? example "View full input data"

    The FHIR generator transforms this structure into a FHIR Condition resource by:

    1. Identifying the section type ("problems") from the dictionary key
    2. Looking up the corresponding FHIR resource type ("Condition") from configuration
    3. Extracting relevant data from the nested structure (codes, dates, statuses)
    4. Using templates to map specific fields to FHIR attributes

    ```python
    {
      "problems": [{
        'act': {
          '@classCode': 'ACT',
          '@moodCode': 'EVN',
          'templateId': [
            {'@root': '2.16.840.1.113883.10.20.1.27'},
            {'@root': '1.3.6.1.4.1.19376.1.5.3.1.4.5.1'},
            {'@root': '1.3.6.1.4.1.19376.1.5.3.1.4.5.2'},
            {'@root': '2.16.840.1.113883.3.88.11.32.7'},
            {'@root': '2.16.840.1.113883.3.88.11.83.7'}
          ],
          'id': {
            '@extension': '51854-concern',
            '@root': '1.2.840.114350.1.13.525.3.7.2.768076'
          },
          'code': {
            '@nullFlavor': 'NA'
          },
          'text': {
            'reference': {'@value': '#problem12'}
          },
          'statusCode': {
            '@code': 'active'
          },
          'effectiveTime': {
            'low': {'@value': '20210317'}
          },
          'entryRelationship': {
            '@typeCode': 'SUBJ',
            '@inversionInd': False,
            'observation': {
              '@classCode': 'OBS',
              '@moodCode': 'EVN',
              'templateId': [
                {'@root': '1.3.6.1.4.1.19376.1.5.3.1.4.5'},
                {'@root': '2.16.840.1.113883.10.20.1.28'}
              ],
              'id': {
                '@extension': '51854',
                '@root': '1.2.840.114350.1.13.525.3.7.2.768076'
              },
              'code': {
                '@code': '64572001',
                '@codeSystem': '2.16.840.1.113883.6.96',
                '@codeSystemName': 'SNOMED CT'
              },
              'text': {
                'reference': {'@value': '#problem12name'}
              },
              'statusCode': {
                '@code': 'completed'
              },
              'effectiveTime': {
                'low': {'@value': '20190517'}
              },
              'value': {
                '@code': '38341003',
                '@codeSystem': '2.16.840.1.113883.6.96',
                '@codeSystemName': 'SNOMED CT',
                '@xsi:type': 'CD',
                '@xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
                'originalText': {
                  'reference': {'@value': '#problem12name'}
                }
              },
              'entryRelationship': {
                '@typeCode': 'REFR',
                '@inversionInd': False,
                'observation': {
                  '@classCode': 'OBS',
                  '@moodCode': 'EVN',
                  'templateId': [
                    {'@root': '2.16.840.1.113883.10.20.1.50'},
                    {'@root': '2.16.840.1.113883.10.20.1.57'},
                    {'@root': '1.3.6.1.4.1.19376.1.5.3.1.4.1.1'}
                  ],
                  'code': {
                    '@code': '33999-4',
                    '@codeSystem': '2.16.840.1.113883.6.1',
                    '@displayName': 'Status'
                  },
                  'statusCode': {
                    '@code': 'completed'
                  },
                  'effectiveTime': {
                    'low': {'@value': '20190517'}
                  },
                  'value': {
                    '@code': '55561003',
                    '@codeSystem': '2.16.840.1.113883.6.96',
                    '@xsi:type': 'CE',
                    '@displayName': 'Active',
                    '@xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance'
                  }
                }
              }
            }
          }
        }
      }]
    }
    ```



<!-- ## HL7v2 Generator

The HL7v2 Generator produces HL7 version 2 messages from FHIR resources (Coming soon!) -->


## Creating a Custom Generator

You can create a custom generator by implementing a class that inherits from `BaseGenerator` and registering it with the engine (this will replace the default generator for the format type):

```python
from healthchain.interop import create_interop, FormatType
from healthchain.interop.config_manager import InteropConfigManager
from healthchain.interop.template_registry import TemplateRegistry
from healthchain.interop.generators import BaseGenerator

from typing import List
from fhir.resources.resource import Resource


class CustomGenerator(BaseGenerator):
    def __init__(self, config: InteropConfigManager, templates: TemplateRegistry):
        super().__init__(config, templates)

    def transform(self, resources: List[Resource], **kwargs) -> str:
        # Generate output from FHIR resources
        return "Custom output format"

# Register the custom generator with the engine
engine = create_interop()
engine.register_generator(FormatType.CDA, CustomGenerator(engine.config, engine.template_registry))
```
