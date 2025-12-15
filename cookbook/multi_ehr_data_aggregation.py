#!/usr/bin/env python3
"""
Multi-Source FHIR Data Aggregation

Demonstrates aggregating patient data from multiple FHIR sources with
simple pipeline processing and provenance tracking.

Requirements:
- pip install healthchain python-dotenv

FHIR Sources:
- Epic Sandbox: Set EPIC_* environment variables
- Cerner Open Sandbox: No auth needed

Run:
- python data_aggregation.py
"""

from typing import List

from dotenv import load_dotenv

from fhir.resources.bundle import Bundle
from fhir.resources.condition import Condition
from fhir.resources.annotation import Annotation

from healthchain.gateway import FHIRGateway, HealthChainAPI
from healthchain.gateway.clients.fhir.base import FHIRAuthConfig
from healthchain.pipeline import Pipeline
from healthchain.io.containers import Document
from healthchain.fhir import merge_bundles


load_dotenv()


# Epic FHIR Sandbox - configure via environment, then build connection string
config = FHIRAuthConfig.from_env("EPIC")
EPIC_URL = config.to_connection_string()

# Cerner Open Sandbox
CERNER_URL = "fhir://fhir-open.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d"


def create_pipeline() -> Pipeline[Document]:
    """Build simple pipeline for demo purposes."""
    pipeline = Pipeline[Document]()

    @pipeline.add_node
    def deduplicate(doc: Document) -> Document:
        """Remove duplicate conditions by resource ID."""
        conditions = doc.fhir.get_resources("Condition")
        unique = list({c.id: c for c in conditions if c.id}.values())
        doc.fhir.add_resources(unique, "Condition", replace=True)
        print(f"Deduplicated {len(unique)} conditions")
        return doc

    @pipeline.add_node
    def add_annotation(doc: Document) -> Document:
        """Add a note to each Condition indicating pipeline processing."""
        conditions = doc.fhir.get_resources("Condition")
        for condition in conditions:
            note_text = "This resource has been processed by healthchain pipeline"
            annotation = Annotation(text=note_text)
            condition.note = (condition.note or []) + [annotation]
        print(f"Added annotation to {len(conditions)} conditions")
        return doc

    return pipeline


def create_app():
    # Initialize gateway and add sources
    gateway = FHIRGateway()
    gateway.add_source("epic", EPIC_URL)
    gateway.add_source("cerner", CERNER_URL)

    pipeline = create_pipeline()

    @gateway.aggregate(Condition)
    def get_unified_patient(patient_id: str, sources: List[str]) -> Bundle:
        """Aggregate conditions for a patient from multiple sources"""
        bundles = []
        for source in sources:
            try:
                bundle = gateway.search(
                    Condition,
                    {"patient": patient_id},
                    source,
                    add_provenance=True,
                    provenance_tag="aggregated",
                )
                bundles.append(bundle)
            except Exception as e:
                print(f"Error from {source}: {e}")

        # Merge bundles - OperationOutcome resources are automatically extracted
        merged_bundle = merge_bundles(bundles, deduplicate=True)

        doc = Document(data=merged_bundle)
        doc = pipeline(doc)

        return doc.fhir.bundle

    app = HealthChainAPI()
    app.register_gateway(gateway)

    return app


if __name__ == "__main__":
    import uvicorn

    app = create_app()
    uvicorn.run(app, port=8888)
    # Runs at: http://127.0.0.1:8888/
