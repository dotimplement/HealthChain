# Migrating from cda_parser to interop

The `interop` module replaces the previous `cda_parser` module with a more flexible and extensible architecture for handling multiple healthcare data formats. This guide will help you migrate your code from the old module to the new one.

## Key Differences

| Feature | cda_parser | interop |
|---------|------------|---------|
| Formats supported | CDA only | CDA, HL7v2, FHIR |
| Primary class | `CdaAnnotator` | `InteropEngine` |
| Data model | Custom CDA model | FHIR resources |
| Configuration | Limited, hardcoded | Extensive, YAML-based |
| Extensibility | Limited | Custom parsers, generators, templates |

## Function Mapping

| CdaAnnotator Method | InteropEngine Equivalent |
|---------------------|--------------------------|
| `CdaAnnotator.from_xml(cda_xml)` | `engine.to_fhir(cda_xml, src_format=FormatType.CDA)` |
| `CdaAnnotator.from_dict(cda_dict)` | No direct equivalent, convert dict to XML first |
| `CdaAnnotator.add_to_problem_list(problems)` | Modify FHIR resources, then use `engine.from_fhir()` |
| `CdaAnnotator.export()` | `engine.from_fhir(resources, dest_format=FormatType.CDA)` |

## Migration Examples

### Reading a CDA Document

#### Before (cda_parser):

```python
from healthchain.cda_parser import CdaAnnotator

# Parse CDA XML
with open("patient_record.xml", "r") as f:
    cda_xml = f.read()

cda = CdaAnnotator.from_xml(cda_xml)

# Access problems, medications, and allergies
problems = cda.problem_list
medications = cda.medication_list
allergies = cda.allergy_list
```

#### After (interop):

```python
from healthchain.interop import create_engine, FormatType

# Create an engine
engine = create_engine()

# Parse CDA XML to FHIR resources
with open("patient_record.xml", "r") as f:
    cda_xml = f.read()

resources = engine.to_fhir(cda_xml, src_format=FormatType.CDA)

# Access problems, medications, and allergies
problems = [r for r in resources if r.resource_type == "Condition"]
medications = [r for r in resources if r.resource_type == "MedicationStatement"]
allergies = [r for r in resources if r.resource_type == "AllergyIntolerance"]
```

### Modifying and Exporting a CDA Document

#### Before (cda_parser):

```python
from healthchain.cda_parser import CdaAnnotator
from fhir.resources.condition import Condition

# Parse CDA XML
with open("patient_record.xml", "r") as f:
    cda_xml = f.read()

cda = CdaAnnotator.from_xml(cda_xml)

# Add a problem
new_problem = Condition(
    resourceType="Condition",
    code={"coding": [{"system": "http://snomed.info/sct", "code": "38341003", "display": "Hypertension"}]},
    subject={"reference": "Patient/123"},
    clinicalStatus={"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]}
)

cda.add_to_problem_list([new_problem])

# Export the updated document
updated_cda_xml = cda.export()
```

#### After (interop):

```python
from healthchain.interop import create_engine, FormatType
from fhir.resources.condition import Condition

# Create an engine
engine = create_engine()

# Parse CDA XML to FHIR resources
with open("patient_record.xml", "r") as f:
    cda_xml = f.read()

resources = engine.to_fhir(cda_xml, src_format=FormatType.CDA)

# Add a problem
new_problem = Condition(
    resourceType="Condition",
    code={"coding": [{"system": "http://snomed.info/sct", "code": "38341003", "display": "Hypertension"}]},
    subject={"reference": "Patient/123"},
    clinicalStatus={"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]}
)

resources.append(new_problem)

# Export the updated document
updated_cda_xml = engine.from_fhir(resources, dest_format=FormatType.CDA)
```

## Advanced Migration

### Custom CDA Sections

If you were working with custom CDA sections in the old module, you'll need to:

1. Define these sections in the configuration:

```yaml
# configs/defaults.yaml
sections:
  custom_section:
    identifiers:
      template_id: "2.16.840.1.113883.10.20.1.XX"
      code: "XXXXX-X"
    resource: "Observation"
    title: "Custom Section"
```

2. Create templates for these sections:

```
# configs/templates/cda/sections/custom_section.xml
<component>
  <section>
    <templateId root="2.16.840.1.113883.10.20.1.XX"/>
    <code code="XXXXX-X" codeSystem="2.16.840.1.113883.6.1" displayName="Custom Section"/>
    <title>Custom Section</title>
    <text>{{ text }}</text>
    {% for entry in entries %}
    {% include entry_template %}
    {% endfor %}
  </section>
</component>
```

### Custom Conversion Logic

If you had custom conversion logic in the old module:

1. Create a custom parser:

```python
from healthchain.interop import FormatType
from healthchain.interop.config_manager import InteropConfigManager

class CustomCDAParser:
    def __init__(self, config: InteropConfigManager):
        self.config = config

    def parse_document(self, cda_xml: str) -> dict:
        # Your custom parsing logic here
        return {"custom_data": "example"}

# Register with the engine
engine.register_parser(FormatType.CDA, CustomCDAParser(engine.config))
```

2. Create a custom generator:

```python
from healthchain.interop import FormatType
from healthchain.interop.config_manager import InteropConfigManager
from healthchain.interop.template_registry import TemplateRegistry
from typing import List
from fhir.resources.resource import Resource

class CustomCDAGenerator:
    def __init__(self, config: InteropConfigManager, templates: TemplateRegistry):
        self.config = config
        self.templates = templates

    def generate_document(self, resources: List[Resource]) -> str:
        # Your custom generation logic here
        return "<ClinicalDocument>Custom XML</ClinicalDocument>"

# Register with the engine
engine.register_generator(FormatType.CDA, CustomCDAGenerator(engine.config, engine.template_registry))
```

## Need Help?

If you encounter issues during migration, please:

1. Check the [full documentation](../interop/index.md) for the interop module
2. Look at the [examples](../../cookbook/interop/basic_conversion.md) for common use cases
3. [Reach out to the community](../../community/index.md) for assistance
