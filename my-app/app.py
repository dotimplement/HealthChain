import os
from typing import List

from fhir.resources.bundle import Bundle
from fhir.resources.condition import Condition

from healthchain.gateway import FHIRGateway, HealthChainAPI
from healthchain.fhir import merge_bundles
from healthchain.io.containers import Document
from healthchain.pipeline import Pipeline

# Add FHIR source credentials to .env (see .env.example)
gateway = FHIRGateway()

epic_url = os.getenv("EPIC_BASE_URL")
cerner_url = os.getenv("CERNER_BASE_URL")

if epic_url:
    gateway.add_source("epic", epic_url)
if cerner_url:
    gateway.add_source("cerner", cerner_url)

# Add your NLP/ML/LLM processing steps here
pipeline = Pipeline[Document]()


@pipeline.add_node
def process(doc: Document) -> Document:
    return doc


@gateway.aggregate(Condition)
def get_patient_conditions(patient_id: str, sources: List[str]) -> Bundle:
    """Aggregate conditions for a patient from all configured FHIR sources."""
    bundles = []
    for source in sources:
        try:
            bundle = gateway.search(
                Condition,
                {"patient": patient_id},
                source,
                add_provenance=True,
            )
            bundles.append(bundle)
        except Exception as e:
            print(f"Error from {source}: {e}")

    merged = merge_bundles(bundles, deduplicate=True)
    doc = pipeline(Document(data=merged))
    return doc.fhir.bundle


app = HealthChainAPI(
    title="My FHIR Gateway",
    description="A multi-EHR data aggregation service built with HealthChain",
)
app.register_gateway(gateway)
