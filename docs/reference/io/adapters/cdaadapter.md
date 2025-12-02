# CDA Adapter

The `CdaAdapter` handles conversion between CDA (Clinical Document Architecture) documents and HealthChain's internal `Document` objects. It parses CDA documents to extract free-text notes and structured clinical data into FHIR resources, and can convert processed Documents back into annotated CDA format.

This adapter is particularly useful for clinical documentation improvement (CDI) workflows where documents need to be processed with ML models and updated with additional structured data.

[(Full Documentation on Clinical Documentation)](../../gateway/soap_cda.md)

## Input and Output

| Input | Output | Document Access |
|-------|--------|-----------------|
| [**CdaRequest**](../../../api/sandbox.md#healthchain.models.requests.cdarequest.CdaRequest) | [**CdaResponse**](../../../api/sandbox.md#healthchain.models.responses.cdaresponse.CdaResponse) | `Document.fhir.problem_list`, `Document.fhir.medication_list`, `Document.text` |

## Document Data Access

Data parsed from the CDA document is converted into FHIR resources and stored in the `Document.fhir` attribute. The adapter supports the following CDA section to FHIR resource mappings:

| CDA Section | FHIR Resource | Document.fhir Attribute |
|-------------|---------------|--------------------------|
| Problem List | [Condition](https://www.hl7.org/fhir/condition.html) | `Document.fhir.problem_list` |
| Medication List | [MedicationStatement](https://www.hl7.org/fhir/medicationstatement.html) | `Document.fhir.medication_list` |
| Clinical Notes | [DocumentReference](https://www.hl7.org/fhir/documentreference.html) | `Document.text` + `Document.fhir.bundle` |

All FHIR resources are Pydantic models, so you can access them using the `model_dump()` method:

```python
# Access structured clinical data
for condition in doc.fhir.problem_list:
    print(condition.model_dump())

# Access free-text content
print(f"Clinical notes: {doc.text}")
```
