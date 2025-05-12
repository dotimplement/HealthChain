"""
FHIR Router for HealthChainAPI.

This module provides router implementations for FHIR resources that
can be registered with the HealthChainAPI.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Path, Body
from typing import Dict, List, Optional


logger = logging.getLogger(__name__)


class FhirRouter(APIRouter):
    """
    Router for FHIR API endpoints.

    This router implements the FHIR REST API for accessing and manipulating
    healthcare resources. It handles capabilities such as:
    - Reading FHIR resources
    - Creating/updating FHIR resources
    - Searching for FHIR resources
    - FHIR operations
    - FHIR batch transactions

    Example:
        ```python
        app = HealthChainAPI()
        app.register_router(FhirRouter)
        ```
    """

    def __init__(
        self,
        prefix: str = "/fhir",
        tags: List[str] = ["FHIR"],
        supported_resources: Optional[List[str]] = None,
        **kwargs,
    ):
        """
        Initialize the FHIR router.

        Args:
            prefix: URL prefix for all routes
            tags: OpenAPI tags for documentation
            supported_resources: List of supported FHIR resource types (None for all)
            **kwargs: Additional arguments to pass to APIRouter
        """
        super().__init__(prefix=prefix, tags=tags, **kwargs)

        self.supported_resources = supported_resources or [
            "Patient",
            "Practitioner",
            "Encounter",
            "Observation",
            "Condition",
            "MedicationRequest",
            "DocumentReference",
        ]

        # Register routes
        self._register_routes()

    def _register_routes(self):
        """Register all FHIR API routes."""

        # Resource instance level operations
        @self.get("/{resource_type}/{id}")
        async def read_resource(
            resource_type: str = Path(..., description="FHIR resource type"),
            id: str = Path(..., description="Resource ID"),
        ):
            """Read a specific FHIR resource instance."""
            self._validate_resource_type(resource_type)
            return {"resourceType": resource_type, "id": id, "status": "generated"}

        @self.put("/{resource_type}/{id}")
        async def update_resource(
            resource: Dict = Body(..., description="FHIR resource"),
            resource_type: str = Path(..., description="FHIR resource type"),
            id: str = Path(..., description="Resource ID"),
        ):
            """Update a specific FHIR resource instance."""
            self._validate_resource_type(resource_type)
            return {"resourceType": resource_type, "id": id, "status": "updated"}

        @self.delete("/{resource_type}/{id}")
        async def delete_resource(
            resource_type: str = Path(..., description="FHIR resource type"),
            id: str = Path(..., description="Resource ID"),
        ):
            """Delete a specific FHIR resource instance."""
            self._validate_resource_type(resource_type)
            return {
                "resourceType": "OperationOutcome",
                "issue": [
                    {
                        "severity": "information",
                        "code": "informational",
                        "diagnostics": f"Successfully deleted {resource_type}/{id}",
                    }
                ],
            }

        # Resource type level operations
        @self.get("/{resource_type}")
        async def search_resources(
            resource_type: str = Path(..., description="FHIR resource type"),
            query_params: Dict = Depends(self._extract_query_params),
        ):
            """Search for FHIR resources."""
            self._validate_resource_type(resource_type)
            return {
                "resourceType": "Bundle",
                "type": "searchset",
                "total": 0,
                "entry": [],
            }

        @self.post("/{resource_type}")
        async def create_resource(
            resource: Dict = Body(..., description="FHIR resource"),
            resource_type: str = Path(..., description="FHIR resource type"),
        ):
            """Create a new FHIR resource."""
            self._validate_resource_type(resource_type)
            return {
                "resourceType": resource_type,
                "id": "generated-id",
                "status": "created",
            }

        # Metadata endpoint
        @self.get("/metadata")
        async def capability_statement():
            """Return the FHIR capability statement."""
            return {
                "resourceType": "CapabilityStatement",
                "status": "active",
                "fhirVersion": "4.0.1",
                "format": ["application/fhir+json"],
                "rest": [
                    {
                        "mode": "server",
                        "resource": [
                            {
                                "type": resource_type,
                                "interaction": [
                                    {"code": "read"},
                                    {"code": "search-type"},
                                ],
                            }
                            for resource_type in self.supported_resources
                        ],
                    }
                ],
            }

    def _validate_resource_type(self, resource_type: str):
        """
        Validate that the requested resource type is supported.

        Args:
            resource_type: FHIR resource type to validate

        Raises:
            HTTPException: If resource type is not supported
        """
        if resource_type not in self.supported_resources:
            raise HTTPException(
                status_code=404,
                detail=f"Resource type {resource_type} is not supported",
            )

    async def _extract_query_params(self, request) -> Dict:
        """
        Extract query parameters from request.

        Args:
            request: FastAPI request object

        Returns:
            Dictionary of query parameters
        """
        return dict(request.query_params)
