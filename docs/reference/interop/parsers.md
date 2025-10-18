# Parsers

Parsers are responsible for extracting structured data from various healthcare document formats. The module includes built-in parsers for common formats like CDA and HL7v2.

## Available Parsers

| Parser | Description |
|--------|-------------|
| `CDAParser` | Parses CDA XML documents into structured data |
| `HL7v2Parser` | Parses HL7v2 messages into structured data |

## CDA Parser

The CDA Parser extracts data from Clinical Document Architecture (CDA) XML documents based on configured section identifiers.

Internally, it uses [xmltodict](https://github.com/martinblech/xmltodict) to parse the XML into a dictionary, validates the dictionary with [Pydantic](https://docs.pydantic.dev/), and then maps each entry to the section keys. See [Working with xmltodict in HealthChain](./xmltodict.md) for more details.

Each extracted entry should be mapped to the name of the corresponding configuration file, which will be used as the `section_key`. The configuration file contains information about the section identifiers that are used to extract the correct section entries.

The input data should be in the format `{<section_key>}: {<section_entries>}`.

([Full Documentation on Configuration](./configuration.md))

### Usage Examples

```python
from healthchain.interop import create_interop, FormatType

# Create an engine
engine = create_interop()

# Parse a CDA document directly to FHIR
with open("tests/data/test_cda.xml", "r") as f:
    cda_xml = f.read()

fhir_resources = engine.to_fhir(cda_xml, src_format=FormatType.CDA)

# Access the CDA parser directly (advanced use case)
cda_parser = engine.cda_parser
sections = cda_parser.parse_document(cda_xml)

# Extract problems section data
problems = sections.get("problems", [])
# parsed CDA section entry in xmltodict format - note that '@' is used to access attributes
# {
#   "act": {
#     "@classCode": "ACT",
#     "@moodCode": "EVN",
#     ...
#   }
# }
```

??? example "View full parsed output"

    This data structure represents a problem (condition) entry from a CDA document, containing:

      - A problem act with template IDs and status
      - An observation with clinical details (SNOMED code 38341003 - Hypertension)
      - Status information (Active)
      - Dates (onset date: May 17, 2019)

    Note how the original XML structure is preserved in dictionary format with '@' used to denote attributes:

    ```python
    [{
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
    ```


### Section Configuration

Sections make up the structure of a CDA document. The CDA parser uses `identifiers` in the section configuration file to determine which sections to extract and map to FHIR resources. Each section is identified by a template ID, code, or both:

```yaml
# Example section configuration
cda:
  sections:
    problems:
      identifiers:
        template_id: "2.16.840.1.113883.10.20.1.11"
        code: "11450-4"
      resource: "Condition"
```

## Creating a Custom Parser

You can create a custom parser by implementing a class that inherits from `BaseParser` and registering it with the engine (this will replace the default parser for the format type):

```python
from healthchain.interop import create_interop, FormatType
from healthchain.interop.config_manager import InteropConfigManager
from healthchain.interop.parsers.base import BaseParser

class CustomParser(BaseParser):
    def __init__(self, config: InteropConfigManager):
        super().__init__(config)

    def from_string(self, data: str) -> dict:
        # Parse the document and return structured data
        return {"structured_data": "example"}

# Register the custom parser with the engine
engine = create_interop()
engine.register_parser(FormatType.CDA, CustomParser(engine.config))
```
