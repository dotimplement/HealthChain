# FHIR Utilities

The `fhir` module provides a set of helper functions to make it easier for you to work with FHIR resources.

## Resource Creation

FHIR is the modern de facto standard for storing and exchanging healthcare data, but working with [FHIR resources](https://www.hl7.org/fhir/resourcelist.html) can often involve complex and nested JSON structures with required and optional fields that vary between contexts.

Creating FHIR resources can involve a lot of boilerplate code, validation errors and manual comparison with FHIR specifications.

For example, as an ML practitioner, you may only care about extracting and inserting certain codes and texts within a FHIR resource. If you want to locate the SNOMED CT code for a medication, you may have to do something headache-inducing like:

```python
medication_statement = {
    "resourceType": "MedicationStatement",
    "status": "active",  # required
    "medication": {  # required
        "concept": {
            "coding": [
                {
                    "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                    "code": "1049221",
                    "display": "Acetaminophen 325 MG Oral Tablet",
                }
            ]
        }
    },
    "subject": {  # required
        "reference": "Patient/example"
    },
}

medication_statement["medication"]["concept"]["coding"][0]["code"]
medication_statement["medication"]["concept"]["coding"][0]["display"]
```

!!! tip "Sensible Defaults for Resource Creation"
    The `fhir` `create_*` functions create FHIR resources with sensible defaults, automatically setting:
      - A reference ID prefixed by "`hc-`"
      - A status of "`active`" (or equivalent)
      - A creation date where necessary

    You can modify and manipulate these resources as you would any other Pydantic object after their creation.

!!! important "Validation of FHIR Resources"
    Internally, HealthChain uses [fhir.resources](https://github.com/nazrulworld/fhir.resources) to validate FHIR resources, which is powered by [Pydantic V2](https://docs.pydantic.dev/latest/).
    These helpers create minimal valid FHIR objects to help you get started easily.
    :octicons-alert-16: **ALWAYS check that the sensible defaults fit your needs, and validate your resource!**

### Overview

| Resource Type | Required Fields | Sensible Defaults | Common Use Cases |
|--------------|-----------------|-------------------|------------------|
| **Condition** | • `clinicalStatus`<br>• `subject` | • `clinicalStatus`: "active"<br>• `id`: auto-generated with "hc-" prefix | • Recording diagnoses<br>• Problem list items<br>• Active conditions |
| **MedicationStatement** | • `subject`<br>• `status`<br>• `medication` | • `status`: "recorded"<br>• `id`: auto-generated with "hc-" prefix | • Current medications<br>• Medication history<br>• Prescribed medications |
| **AllergyIntolerance** | • `patient` | • `id`: auto-generated with "hc-" prefix | • Allergies<br>• Intolerances<br>• Adverse reactions |
| **DocumentReference** | • `type` | • `status`: "current"<br>• `date`: UTC now<br>• `description`: default text<br>• `content.attachment.title`: default text | • Clinical notes<br>• Lab reports<br>• Imaging reports |

---

### create_condition()

Creates a new [**Condition**](https://www.hl7.org/fhir/condition.html) resource.

!!! note "Required fields"
    - [clinicalStatus](https://www.hl7.org/fhir/condition-definitions.html#Condition.clinicalStatus)
    - [subject](https://www.hl7.org/fhir/condition-definitions.html#Condition.subject)

!!! tip "Sensible Defaults"
    `clinicalStatus` is set to "`active`"

```python
from healthchain.fhir import create_condition

# Create a condition representing hypertension
condition = create_condition(
    subject="Patient/123",
    code="38341003",
    display="Hypertension",
    system="http://snomed.info/sct",
)

# Output the created resource
print(condition.model_dump())
```

??? example "Example Output JSON"
    ```json
    {
        "resourceType": "Condition",
        "id": "hc-3117bdce-bfab-4d71-968b-1ded900882ca",
        "clinicalStatus": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                "code": "active",
                "display": "Active"
            }]
        },
        "code": {
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "38341003",
                "display": "Hypertension"
            }]
        },
        "subject": {
            "reference": "Patient/123"
        }
    }
    ```

---

### create_medication_statement()

Creates a new [**MedicationStatement**](https://www.hl7.org/fhir/medicationstatement.html) resource.

!!! note "Required fields"
    - [subject](https://www.hl7.org/fhir/medicationstatement-definitions.html#MedicationStatement.subject)
    - [status](https://www.hl7.org/fhir/medicationstatement-definitions.html#MedicationStatement.status)
    - [medication](https://www.hl7.org/fhir/medicationstatement-definitions.html#MedicationStatement.medication)

!!! tip "Sensible Defaults"
    `status` is set to "`recorded`"

```python
from healthchain.fhir import create_medication_statement

# Create a medication statement for Acetaminophen
medication = create_medication_statement(
    subject="Patient/123",
    code="1049221",
    display="Acetaminophen 325 MG Oral Tablet",
    system="http://www.nlm.nih.gov/research/umls/rxnorm",
)

# Output the created resource
print(medication.model_dump())
```

??? example "Example Output JSON"
    ```json
    {
        "resourceType": "MedicationStatement",
        "id": "hc-86a26eba-63f9-4017-b7b2-5b36f9bad5f1",
        "status": "recorded",
        "medication": {
            "concept": {
                "coding": [{
                    "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                    "code": "1049221",
                    "display": "Acetaminophen 325 MG Oral Tablet"
                }]
            }
        },
        "subject": {
            "reference": "Patient/123"
        }
    }
    ```

---

### create_allergy_intolerance()

Creates a new [**AllergyIntolerance**](https://www.hl7.org/fhir/allergyintolerance.html) resource.

!!! note "Required fields"
    - [patient](https://www.hl7.org/fhir/allergyintolerance-definitions.html#AllergyIntolerance.patient)

!!! tip "Sensible Defaults"
    None (besides the auto-generated id)

```python
from healthchain.fhir import create_allergy_intolerance

# Create an allergy intolerance record
allergy = create_allergy_intolerance(
    patient="Patient/123",
    code="418038007",
    display="Propensity to adverse reactions to substance",
    system="http://snomed.info/sct"
)

# Output the created resource
print(allergy.model_dump())
```

??? example "Example Output JSON"
    ```json
    {
        "resourceType": "AllergyIntolerance",
        "id": "hc-65edab39-d90b-477b-bdb5-a173b21efd44",
        "code": {
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "418038007",
                "display": "Propensity to adverse reactions to substance"
            }]
        },
        "patient": {
            "reference": "Patient/123"
        }
    }
    ```

---

### create_document_reference()

Creates a new [**DocumentReference**](https://www.hl7.org/fhir/documentreference.html) resource. Handles base64 encoding of the attachment data.

!!! note "Required fields"
    - [type](https://www.hl7.org/fhir/documentreference-definitions.html#DocumentReference.type)

!!! tip "Sensible Defaults"
    - `type` is set to "`collection`"
    - `status` is set to "`current`"
    - `date` is set to the current UTC timestamp
    - `description` is set to "`DocumentReference created by HealthChain`"
    - `content[0].attachment.title` is set to "`Attachment created by HealthChain`"

```python
from healthchain.fhir import create_document_reference

# Create a document reference with a simple text attachment
doc_ref = create_document_reference(
    data="Hello World",
    content_type="text/plain",
    description="A simple text document"
)

# Output the created resource
print(doc_ref.model_dump())
```

??? example "Example Output JSON"
    ```json
    {
        "resourceType": "DocumentReference",
        "id": "hc-60fcfdad-9617-4557-88d8-8c8db9b9fe70",
        "status": "current",
        "date": "2025-02-28T14:55:33+00:00",
        "description": "A simple text document",
        "content": [{
            "attachment": {
                "contentType": "text/plain",
                "data": "SGVsbG8gV29ybGQ=",
                "title": "Attachment created by HealthChain",
                "creation": "2025-02-28T14:55:33+00:00"
            }
        }]
    }
    ```

    ??? example "View Decoded Content"
        ```text
        Hello World
        ```

---

## Utilities

### set_problem_list_item_category()

Sets the category of a [**Condition**](https://www.hl7.org/fhir/condition.html) resource to "`problem-list-item`".

```python
from healthchain.fhir import set_problem_list_item_category, create_condition

# Create a condition and set it as a problem list item
problem_list_item = create_condition(
    subject="Patient/123",
    code="38341003",
    display="Hypertension"
)

set_problem_list_item_category(problem_list_item)

# Output the modified resource
print(problem_list_item.model_dump())
```

??? example "Example Output JSON"
    ```json
    {
        "resourceType": "Condition",
        "id": "hc-3d5f62e7-729b-4da1-936c-e8e16e5a9358",
        "clinicalStatus": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                "code": "active",
                "display": "Active"
            }]
        },
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-category",
                "code": "problem-list-item",
                "display": "Problem List Item"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "38341003",
                "display": "Hypertension"
            }]
        },
        "subject": {
            "reference": "Patient/123"
        }
    }
    ```

---

### read_content_attachment()

Reads attachments from a [**DocumentReference**](https://www.hl7.org/fhir/documentreference.html) in a human-readable format.

```python
from healthchain.fhir import read_content_attachment

attachments = read_content_attachment(document_reference)
# Returns a list of dictionaries containing:
# [
#     {
#         "data": "Hello World",
#         "metadata": {
#             "content_type": "text/plain",
#             "title": "My Document",
#             "creation": datetime.datetime(2025, 2, 28, 15, 27, 55, tzinfo=TzInfo(UTC)),
#         },
#     }
# ]
```

---

## Bundle Operations

FHIR Bundles are containers that can hold multiple FHIR resources together. They are commonly used to group related resources or to send/receive multiple resources in a single request.

The bundle operations make it easy to:

- Create and manage bundles
- Add or update resources within bundles
- Retrieve specific resource types from bundles
- Work with multiple resource types in a single bundle

---

### create_bundle()

Creates a new [**Bundle**](https://www.hl7.org/fhir/bundle.html) resource.

!!! note "Required field"
    - [type](https://www.hl7.org/fhir/bundle-definitions.html#Bundle.type)

!!! tip "Sensible Defaults"
    `type` is set to "`collection`"

```python
from healthchain.fhir import create_bundle

# Create an empty bundle
bundle = create_bundle(bundle_type="collection")

# Output the created resource
print(bundle.model_dump())
```

??? example "Example Output JSON"
    ```json
    {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": []
    }
    ```

---

### add_resource()

Adds a single resource to a [**Bundle**](https://www.hl7.org/fhir/bundle.html).

```python
from healthchain.fhir import add_resource, create_condition, create_bundle

# Create a condition to add to the bundle
condition = create_condition(
    subject="Patient/123",
    code="38341003",
    display="Hypertension"
)

# Create a bundle and add the condition
bundle = create_bundle()
add_resource(bundle, condition)

# Output the modified bundle
print(bundle.model_dump())
```

??? example "Example Output JSON"
    ```json
    {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [{
            "resource": {
                "resourceType": "Condition",
                "id": "hc-3117bdce-bfab-4d71-968b-1ded900882ca",
                "clinicalStatus": {
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                        "code": "active",
                        "display": "Active"
                    }]
                },
                "code": {
                    "coding": [{
                        "system": "http://snomed.info/sct",
                        "code": "38341003",
                        "display": "Hypertension"
                    }]
                },
                "subject": {
                    "reference": "Patient/123"
                }
            }
        }]
    }
    ```

    ??? info "Field Descriptions"
        | Field | Required | Description |
        |-------|:--------:|-------------|
        | `entry` | - | Array of resources in the bundle |
        | `entry[].resource` | ✓ | The FHIR resource being added |
        | `entry[].fullUrl` | - | Optional full URL for the resource |

---

### get_resources()

Retrieves all resources of a specific type from a [**Bundle**](https://www.hl7.org/fhir/bundle.html).

```python
from healthchain.fhir import get_resources

# Get all conditions in the bundle
conditions = get_resources(bundle, "Condition")

# Or using the resource type directly
from fhir.resources.condition import Condition
conditions = get_resources(bundle, Condition)

for condition in conditions:
    print(f"Found condition: {condition.code.coding[0].display}")
```

---

### set_resources()

Sets or updates resources of a specific type in a [**Bundle**](https://www.hl7.org/fhir/bundle.html).

```python
from healthchain.fhir import set_resources, create_condition

# Create some conditions
conditions = [
    create_condition(
        subject="Patient/123",
        code="38341003",
        display="Hypertension"
    ),
    create_condition(
        subject="Patient/123",
        code="44054006",
        display="Diabetes"
    )
]

# Replace all existing conditions with new ones
set_resources(bundle, conditions, "Condition", replace=True)

# Or append new conditions to existing ones
set_resources(bundle, conditions, "Condition", replace=False)
```

??? example "Bundle with Multiple Conditions"
    ```json
    {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {
                "resource": {
                    "resourceType": "Condition",
                    "id": "hc-3117bdce-bfab-4d71-968b-1ded900882ca",
                    "clinicalStatus": {
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                            "code": "active",
                            "display": "Active"
                        }]
                    },
                    "code": {
                        "coding": [{
                            "system": "http://snomed.info/sct",
                            "code": "38341003",
                            "display": "Hypertension"
                        }]
                    },
                    "subject": {"reference": "Patient/123"}
                }
            },
            {
                "resource": {
                    "resourceType": "Condition",
                    "id": "hc-9876fedc-ba98-7654-3210-fedcba987654",
                    "clinicalStatus": {
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                            "code": "active",
                            "display": "Active"
                        }]
                    },
                    "code": {
                        "coding": [{
                            "system": "http://snomed.info/sct",
                            "code": "44054006",
                            "display": "Diabetes"
                        }]
                    },
                    "subject": {"reference": "Patient/123"}
                }
            }
        ]
    }
    ```

---

### merge_bundles()

Merges multiple FHIR [**Bundle**](https://www.hl7.org/fhir/bundle.html) resources into a single bundle.

- Resources from each bundle are combined into a single output bundle of `type: collection`.
- All entries from all input bundles will appear in the resulting bundle's `entry` array.
- If bundles have the same resource (e.g. matching `id` or identical resources), they will *all* be included unless you handle duplicates before/after calling `merge_bundles`.

```python
from healthchain.fhir import merge_bundles, create_bundle, create_condition

# Create two bundles with different resources
bundle1 = create_bundle()
add_resource(bundle1, create_condition(
    subject="Patient/123", code="38341003", display="Hypertension"
))
bundle2 = create_bundle()
add_resource(bundle2, create_condition(
    subject="Patient/123", code="44054006", display="Diabetes"
))

# Merge the bundles together
merged = merge_bundles(bundle1, bundle2)

# Output the merged bundle
print(merged.model_dump())
```

??? example "Example Output JSON"
    ```json
    {
      "resourceType": "Bundle",
      "type": "collection",
      "entry": [
        {
          "resource": {
            "resourceType": "Condition",
            "id": "hc-3117bdce-bfab-4d71-968b-1ded900882ca",
            "clinicalStatus": {
              "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                "code": "active",
                "display": "Active"
              }]
            },
            "code": {
              "coding": [{
                "system": "http://snomed.info/sct",
                "code": "38341003",
                "display": "Hypertension"
              }]
            },
            "subject": { "reference": "Patient/123" }
          }
        },
        {
          "resource": {
            "resourceType": "Condition",
            "id": "hc-9876fedc-ba98-7654-3210-fedcba987654",
            "clinicalStatus": {
              "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                "code": "active",
                "display": "Active"
              }]
            },
            "code": {
              "coding": [{
                "system": "http://snomed.info/sct",
                "code": "44054006",
                "display": "Diabetes"
              }]
            },
            "subject": { "reference": "Patient/123" }
          }
        }
      ]
    }
    ```

---

## Common Patterns

### Working with Multiple Resource Types

This example shows how to work with multiple types of FHIR resources in a single bundle.

```python
from healthchain.fhir import (
    create_bundle,
    create_condition,
    create_medication_statement,
    create_allergy_intolerance,
    get_resources,
    set_resources,
)

# Create a bundle to hold patient data
bundle = create_bundle()

# Add conditions (diagnoses)
conditions = [
    create_condition(
        subject="Patient/123",
        code="38341003",
        display="Hypertension"
    ),
    create_condition(
        subject="Patient/123",
        code="44054006",
        display="Diabetes"
    )
]
set_resources(bundle, conditions, "Condition")

# Add medications
medications = [
    create_medication_statement(
        subject="Patient/123",
        code="1049221",
        display="Acetaminophen 325 MG"
    )
]
set_resources(bundle, medications, "MedicationStatement")

# Add allergies
allergies = [
    create_allergy_intolerance(
        patient="Patient/123",
        code="418038007",
        display="Penicillin allergy"
    )
]
set_resources(bundle, allergies, "AllergyIntolerance")

# Later, retrieve resources by type
conditions = get_resources(bundle, "Condition")
medications = get_resources(bundle, "MedicationStatement")
allergies = get_resources(bundle, "AllergyIntolerance")
```

??? example "Complete Bundle Example Output"
    ```json
    {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {
                "resource": {
                    "resourceType": "Condition",
                    "id": "hc-3117bdce-bfab-4d71-968b-1ded900882ca",
                    "clinicalStatus": {
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                            "code": "active",
                            "display": "Active"
                        }]
                    },
                    "code": {
                        "coding": [{
                            "system": "http://snomed.info/sct",
                            "code": "38341003",
                            "display": "Hypertension"
                        }]
                    },
                    "subject": {"reference": "Patient/123"}
                }
            },
            {
                "resource": {
                    "resourceType": "Condition",
                    "id": "hc-9876fedc-ba98-7654-3210-fedcba987654",
                    "clinicalStatus": {
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                            "code": "active",
                            "display": "Active"
                        }]
                    },
                    "code": {
                        "coding": [{
                            "system": "http://snomed.info/sct",
                            "code": "44054006",
                            "display": "Diabetes"
                        }]
                    },
                    "subject": {"reference": "Patient/123"}
                }
            },
            {
                "resource": {
                    "resourceType": "MedicationStatement",
                    "id": "hc-86a26eba-63f9-4017-b7b2-5b36f9bad5f1",
                    "status": "recorded",
                    "medication": {
                        "concept": {
                            "coding": [{
                                "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                                "code": "1049221",
                                "display": "Acetaminophen 325 MG"
                            }]
                        }
                    },
                    "subject": {"reference": "Patient/123"}
                }
            },
            {
                "resource": {
                    "resourceType": "AllergyIntolerance",
                    "id": "hc-65edab39-d90b-477b-bdb5-a173b21efd44",
                    "code": {
                        "coding": [{
                            "system": "http://snomed.info/sct",
                            "code": "418038007",
                            "display": "Penicillin allergy"
                        }]
                    },
                    "patient": {"reference": "Patient/123"}
                }
            }
        ]
    }
    ```
