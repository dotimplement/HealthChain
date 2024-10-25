# CDA Parser

The `CdaAnnotator` class is responsible for parsing and annotating CDA (Clinical Document Architecture) documents. It extracts information about problems, medications, allergies, and notes from the CDA document, and allows you to add new information to the CDA document.

The CDA parser is used in the [CDA Connector](../pipeline/connectors/cdaconnector.md) module, but can also be used independently.

Internally, `CdaAnnotator` parses CDA documents from XML strings to a dictionary-based representation using `xmltodict` and uses Pydantic for data validation. New problems are added to the CDA document using a template-based approach. It's currently not super configurable, but we're working on it.

Data interacts with the `CdaAnnotator` through `Concept` data models, which are designed to be an system-agnostic intermediary between FHIR and CDA data representations.

[(CdaAnnotator API Reference](../../api/cda_parser.md) [| Concept API Reference)](../../api/data_models.md#healthchain.models.data.concept)

## Usage

### Parsing CDA documents

Parse a CDA document from an XML string:

```python
from healthchain.cda_parser import CdaAnnotator

cda = CdaAnnotator.from_xml(cda_xml_string)

problems = cda.problem_list
medications = cda.medication_list
allergies = cda.allergy_list
note = cda.note

print([problem.name for problem in problems])
print([medication.name for medication in medications])
print([allergy.name for allergy in allergies])
print(note)
```

You can access data parsed from the CDA document in the `problem_list`, `medication_list`, `allergy_list`, and `note` attributes of the `CdaAnnotator` instance. They return a list of `Concept` data models.

### Adding new information to the CDA document

The methods currently available for adding new information to the CDA document are:

| Method | Description |
|--------|-------------|
| `.add_to_problem_list()` | Adds a list of [ProblemConcept](../../api/data_models.md#healthchain.models.data.concept.ProblemConcept) |
| `.add_to_medication_list()` | Adds a list of [MedicationConcept](../../api/data_models.md#healthchain.models.data.concept.MedicationConcept) |
| `.add_to_allergy_list()` | Adds a list of [AllergyConcept](../../api/data_models.md#healthchain.models.data.concept.AllergyConcept) |

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
from healthchain.models import ProblemConcept, MedicationConcept, AllergyConcept

cda = CdaAnnotator.from_xml(cda_xml_string)

new_problems = [ProblemConcept(name="New Problem", code="123456")]
new_medications = [MedicationConcept(name="New Medication", code="789012")]
new_allergies = [AllergyConcept(name="New Allergy", code="345678")]

# Add new problems, medications, and allergies
cda.add_to_problem_list(new_problems, overwrite=True)
cda.add_to_medication_list(new_medications, overwrite=True)
cda.add_to_allergy_list(new_allergies, overwrite=True)

# Export the modified CDA document
modified_cda_xml = cda.export()
```

The CDA parser is a work in progress. I'm just gonna be real with you, CDAs are the bane of my existence. If you, for some reason, love working with XML-based documents, please get [in touch](https://discord.gg/UQC6uAepUz)! We have plans to implement more functionality in the future, including allowing configurable templates, more CDA section methods, and using LLMs as a fallback parsing method.
