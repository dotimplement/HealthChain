# CDS FHIR Adapter

The `CdsFhirAdapter` handles conversion between CDS Hooks requests/responses and HealthChain's internal `Document` objects. It processes FHIR data in the context of Clinical Decision Support (CDS) services, following the [CDS Hooks specification](https://cds-hooks.org/).

This adapter is specifically designed for building CDS services that receive FHIR data through prefetch and return clinical decision cards.

[(Full Documentation on Clinical Decision Support)](../../gateway/cdshooks.md)

## Input and Output

| Input | Output | Document Access |
|-------|--------|-----------------|
| [**CDSRequest**](../../../api/sandbox.md#healthchain.models.requests.cdsrequest.CDSRequest) | [**CDSResponse**](../../../api/sandbox.md#healthchain.models.responses.cdsresponse.CDSResponse) | `Document.fhir.get_prefetch_resources()`, `Document.cds.cards` |


## Document Data Access

### FHIR Prefetch Resources

Data from the CDS request's `prefetch` field is stored in the `Document.fhir.prefetch_resources` attribute as a dictionary mapping prefetch keys to FHIR resources:

```python
# After processing with adapter.parse()
doc = adapter.parse(cds_request)

# Access prefetch resources by key
patient = doc.fhir.get_prefetch_resources("patient")
conditions = doc.fhir.get_prefetch_resources("condition")
document_ref = doc.fhir.get_prefetch_resources("document")

# Access all prefetch resources
all_resources = doc.fhir.prefetch_resources
for key, resource in all_resources.items():
    print(f"Resource '{key}': {resource.resourceType}")
```

### CDS Cards

Generated CDS cards are stored in the `Document.cds.cards` attribute:

```python
# After ML processing
for card in processed_doc.cds.cards:
    print(f"Summary: {card.summary}")
    print(f"Indicator: {card.indicator}")
    print(f"Detail: {card.detail}")
    print(f"Source: {card.source}")
```

### Document Text Extraction

When the prefetch contains a `DocumentReference` resource, the adapter automatically extracts the document content and stores it in `Document.text`:

```python
# If prefetch contains document with base64 content
cds_request = CDSRequest(
    prefetch={
        "document": {
            "resourceType": "DocumentReference",
            "content": [{
                "attachment": {
                    "contentType": "text/plain",
                    "data": "UGF0aWVudCBkaXNjaGFyZ2Ugbm90ZXM="  # base64 encoded
                }
            }]
        }
    }
)

doc = adapter.parse(cds_request)
print(doc.text)  # "Patient discharge notes" (decoded)
```
