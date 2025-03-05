# CDA Parser

The `CdaAnnotator` class is responsible for parsing and annotating CDA (Clinical Document Architecture) documents. It extracts information about problems, medications, allergies, and notes from the CDA document into FHIR resources, and allows you to add new information to the CDA document.

The CDA parser is used in the [CDA Connector](../pipeline/connectors/cdaconnector.md) module, but can also be used independently.

[(CdaAnnotator API Reference)](../../api/cda_parser.md)

## Usage

### Parsing CDA documents

Parse a CDA document from an XML string:

```python
from healthchain.cda_parser import CdaAnnotator

with open("tests/data/test_cda.xml", "r") as f:
    cda_xml_string = f.read()

cda = CdaAnnotator.from_xml(cda_xml_string)

conditions = cda.problem_list
medications = cda.medication_list
allergies = cda.allergy_list
note = cda.note

print([condition.model_dump() for condition in conditions])
print([medication.model_dump() for medication in medications])
print([allergy.model_dump() for allergy in allergies])
print(note)
```

You can access data parsed from the CDA document in the `problem_list`, `medication_list`, `allergy_list`, and `note` attributes of the `CdaAnnotator` instance. They return a list of FHIR `Condition`, `MedicationStatement`, and `AllergyIntolerance` resources.

### Adding new information to the CDA document

The methods currently available for adding new information to the CDA document are:

| Method | Description |
|--------|-------------|
| `.add_to_problem_list()` | Adds a list of [FHIR Condition](https://www.hl7.org/fhir/condition.html) resources |
| `.add_to_medication_list()` | Adds a list of [FHIR MedicationStatement](https://www.hl7.org/fhir/medicationstatement.html) resources |
| `.add_to_allergy_list()` | Adds a list of [FHIR AllergyIntolerance](https://www.hl7.org/fhir/allergyintolerance.html) resources |

The `overwrite` parameter in the `add_to_*_list()` methods is used to determine whether to overwrite the existing list or append to it. If `overwrite` is `True`, the existing list will be replaced with the new list. If `overwrite` is `False`, the new list will be appended to the existing list.

Depending on the use case, you don't always need to return the original list of information in the CDA document you receive, although this is mostly useful if you are just developing and don't want the eye-strain of a lengthy CDA document.

### Exporting the CDA document

```python
xml_string = cda.export(pretty_print=True)
```

The `pretty_print` parameter is optional and defaults to `True`. If `pretty_print` is `True`, the XML string will be formatted with newlines and indentation.

## Example

```python
from healthchain.cda_parser import CdaAnnotator
from healthchain.fhir import (
    create_condition,
    create_medication_statement,
    create_allergy_intolerance,
)

with open("tests/data/test_cda.xml", "r") as f:
    cda_xml_string = f.read()

cda = CdaAnnotator.from_xml(cda_xml_string)

new_problems = [
    create_condition(subject="Patient/123", code="123456", display="New Problem")
]
new_medications = [
    create_medication_statement(
        subject="Patient/123", code="789012", display="New Medication"
    )
]
new_allergies = [
    create_allergy_intolerance(
        patient="Patient/123", code="345678", display="New Allergy"
    )
]

# Add new problems, medications, and allergies
cda.add_to_problem_list(new_problems, overwrite=True)
cda.add_to_medication_list(new_medications, overwrite=True)
cda.add_to_allergy_list(new_allergies, overwrite=True)

# Export the modified CDA document
modified_cda_xml = cda.export()

print(modified_cda_xml)

```

The CDA parser is a work in progress. I'm just gonna be real with you, CDAs are the bane of my existence. If you, for some reason, love working with XML-based documents, please get [in touch](https://discord.gg/UQC6uAepUz)! We have plans to implement more functionality in the future, including allowing configurable templates, more CDA section methods, and using LLMs as a fallback parsing method.
