"""
Healthcare Data Conversion Service - FastAPI-based REST API.

Provides HTTP endpoints for healthcare data format conversion operations.
Built on HealthChain's gateway framework.
"""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from healthcare_data_converter.converter import HealthcareDataConverter
from healthcare_data_converter.models import (
    BatchConversionRequest,
    BatchConversionResponse,
    ConversionCapabilities,
    ConversionFormat,
    ConversionRequest,
    ConversionResponse,
    ConversionStatus,
    DocumentType,
    HealthCheckResponse,
    ValidationLevel,
)

logger = logging.getLogger(__name__)

# Thread pool for CPU-bound conversion operations
_executor = ThreadPoolExecutor(max_workers=4)


class ConversionService:
    """
    FastAPI-based conversion service.

    Provides REST API endpoints for healthcare data format conversion
    with support for single and batch operations.

    Examples:
        Create and run the service:
        ```python
        service = ConversionService()
        app = service.create_app()

        # Run with uvicorn
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)
        ```

        Or use the convenience method:
        ```python
        service = ConversionService()
        service.run(host="0.0.0.0", port=8000)
        ```
    """

    def __init__(
        self,
        converter: Optional[HealthcareDataConverter] = None,
        enable_cors: bool = True,
        cors_origins: Optional[list[str]] = None,
        api_prefix: str = "/api/v1",
    ):
        """
        Initialize the conversion service.

        Args:
            converter: HealthcareDataConverter instance (creates default if None)
            enable_cors: Enable CORS middleware
            cors_origins: Allowed CORS origins (defaults to ["*"])
            api_prefix: API route prefix
        """
        self.converter = converter or HealthcareDataConverter()
        self.enable_cors = enable_cors
        self.cors_origins = cors_origins or ["*"]
        self.api_prefix = api_prefix
        self._app: Optional[FastAPI] = None

    def create_app(self) -> FastAPI:
        """Create and configure the FastAPI application."""

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            """Application lifespan manager."""
            logger.info("Healthcare Data Conversion Service starting...")
            yield
            logger.info("Healthcare Data Conversion Service shutting down...")
            _executor.shutdown(wait=True)

        app = FastAPI(
            title="Healthcare Data Format Conversion API",
            description="""
            A RESTful API for converting healthcare data between FHIR and CDA formats.

            ## Features
            - Bidirectional FHIR ↔ CDA conversion
            - HL7v2 → FHIR conversion
            - Configuration-driven templates
            - Batch processing support
            - Validation at multiple strictness levels

            ## Supported Formats
            - **FHIR R4**: JSON-based modern healthcare interoperability standard
            - **CDA**: XML-based Clinical Document Architecture
            - **HL7v2**: Legacy message format (to FHIR only)

            ## Document Types
            Supports multiple CDA document types including CCD, Discharge Summary,
            Progress Notes, and more.
            """,
            version="1.0.0",
            lifespan=lifespan,
            docs_url="/docs",
            redoc_url="/redoc",
            openapi_url="/openapi.json",
        )

        # Configure CORS
        if self.enable_cors:
            app.add_middleware(
                CORSMiddleware,
                allow_origins=self.cors_origins,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

        # Register routes
        self._register_routes(app)

        self._app = app
        return app

    def _register_routes(self, app: FastAPI):
        """Register API routes."""

        @app.get(
            "/health",
            response_model=HealthCheckResponse,
            tags=["Health"],
            summary="Health check endpoint",
        )
        async def health_check():
            """Check service health and get basic info."""
            return HealthCheckResponse(
                status="healthy",
                version="1.0.0",
                supported_formats=[f.value for f in ConversionFormat],
                supported_document_types=[dt.value for dt in DocumentType],
            )

        @app.get(
            f"{self.api_prefix}/capabilities",
            response_model=ConversionCapabilities,
            tags=["Info"],
            summary="Get conversion capabilities",
        )
        async def get_capabilities():
            """Get detailed information about supported conversion capabilities."""
            return self.converter.get_capabilities()

        @app.post(
            f"{self.api_prefix}/convert",
            response_model=ConversionResponse,
            tags=["Conversion"],
            summary="Convert healthcare data",
            responses={
                200: {"description": "Conversion successful"},
                400: {"description": "Invalid request"},
                422: {"description": "Validation error"},
                500: {"description": "Conversion error"},
            },
        )
        async def convert(request: ConversionRequest):
            """
            Convert healthcare data between formats.

            Supports the following conversions:
            - CDA → FHIR
            - FHIR → CDA
            - HL7v2 → FHIR

            The request body should contain:
            - `data`: The source data (XML for CDA/HL7v2, JSON for FHIR)
            - `source_format`: The format of the source data
            - `target_format`: The desired output format
            - `document_type`: (Optional) CDA document type when converting to CDA
            - `validation_level`: (Optional) Validation strictness level
            """
            try:
                # Run conversion in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    _executor, self.converter.convert, request
                )

                if response.status == ConversionStatus.FAILED:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "message": "Conversion failed",
                            "errors": response.errors,
                        },
                    )

                return response

            except HTTPException:
                raise
            except Exception as e:
                logger.exception(f"Conversion error: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={"message": "Internal conversion error", "error": str(e)},
                )

        @app.post(
            f"{self.api_prefix}/convert/batch",
            response_model=BatchConversionResponse,
            tags=["Conversion"],
            summary="Batch convert healthcare data",
        )
        async def batch_convert(request: BatchConversionRequest):
            """
            Convert multiple healthcare documents in a single request.

            Supports up to 100 documents per batch. Documents can be processed
            in parallel for better performance.
            """
            start_time = time.perf_counter()
            results = []
            failed_count = 0

            if request.parallel:
                # Process in parallel using thread pool
                loop = asyncio.get_event_loop()
                tasks = [
                    loop.run_in_executor(_executor, self.converter.convert, doc)
                    for doc in request.documents
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Handle exceptions
                processed_results = []
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        failed_count += 1
                        processed_results.append(
                            ConversionResponse(
                                status=ConversionStatus.FAILED,
                                data=None,
                                metadata=request.documents[i].model_dump(),
                                errors=[str(result)],
                            )
                        )
                        if request.stop_on_error:
                            break
                    else:
                        if result.status == ConversionStatus.FAILED:
                            failed_count += 1
                        processed_results.append(result)

                results = processed_results
            else:
                # Process sequentially
                for doc in request.documents:
                    try:
                        result = self.converter.convert(doc)
                        results.append(result)
                        if result.status == ConversionStatus.FAILED:
                            failed_count += 1
                            if request.stop_on_error:
                                break
                    except Exception as e:
                        failed_count += 1
                        results.append(
                            ConversionResponse(
                                status=ConversionStatus.FAILED,
                                data=None,
                                metadata=doc.model_dump(),
                                errors=[str(e)],
                            )
                        )
                        if request.stop_on_error:
                            break

            elapsed_ms = (time.perf_counter() - start_time) * 1000

            return BatchConversionResponse(
                total=len(request.documents),
                successful=len(results) - failed_count,
                failed=failed_count,
                results=results,
                processing_time_ms=round(elapsed_ms, 2),
            )

        @app.post(
            f"{self.api_prefix}/validate/cda",
            tags=["Validation"],
            summary="Validate CDA document",
        )
        async def validate_cda(
            cda_xml: str,
        ):
            """Validate a CDA XML document against the schema."""
            is_valid, messages = self.converter.validate_cda(cda_xml)
            return {
                "valid": is_valid,
                "messages": messages,
            }

        @app.post(
            f"{self.api_prefix}/validate/fhir",
            tags=["Validation"],
            summary="Validate FHIR resources",
        )
        async def validate_fhir(
            fhir_data: dict,
        ):
            """Validate FHIR resources against the specification."""
            is_valid, messages = self.converter.validate_fhir(fhir_data)
            return {
                "valid": is_valid,
                "messages": messages,
            }

        @app.get(
            f"{self.api_prefix}/formats",
            tags=["Info"],
            summary="List supported formats",
        )
        async def list_formats():
            """Get list of supported data formats."""
            return {
                "formats": [
                    {
                        "id": f.value,
                        "name": f.name,
                        "description": self._get_format_description(f),
                    }
                    for f in ConversionFormat
                ]
            }

        @app.get(
            f"{self.api_prefix}/document-types",
            tags=["Info"],
            summary="List supported document types",
        )
        async def list_document_types():
            """Get list of supported CDA document types."""
            return {
                "document_types": [
                    {
                        "id": dt.value,
                        "name": dt.name.replace("_", " ").title(),
                        "description": self._get_document_type_description(dt),
                    }
                    for dt in DocumentType
                ]
            }

    def _get_format_description(self, fmt: ConversionFormat) -> str:
        """Get description for a format."""
        descriptions = {
            ConversionFormat.FHIR: "FHIR R4 - Fast Healthcare Interoperability Resources",
            ConversionFormat.CDA: "CDA R2 - Clinical Document Architecture",
            ConversionFormat.HL7V2: "HL7 Version 2.x - Legacy messaging format",
        }
        return descriptions.get(fmt, "")

    def _get_document_type_description(self, doc_type: DocumentType) -> str:
        """Get description for a document type."""
        descriptions = {
            DocumentType.CCD: "Continuity of Care Document - Summary of patient's medical information",
            DocumentType.DISCHARGE_SUMMARY: "Summary of hospital stay and discharge instructions",
            DocumentType.PROGRESS_NOTE: "Documentation of patient encounter or visit",
            DocumentType.CONSULTATION_NOTE: "Specialist consultation documentation",
            DocumentType.HISTORY_AND_PHYSICAL: "Initial assessment and examination",
            DocumentType.OPERATIVE_NOTE: "Surgical procedure documentation",
            DocumentType.PROCEDURE_NOTE: "Non-surgical procedure documentation",
            DocumentType.REFERRAL_NOTE: "Referral to another provider",
        }
        return descriptions.get(doc_type, "")

    def run(
        self,
        host: str = "0.0.0.0",
        port: int = 8000,
        reload: bool = False,
        log_level: str = "info",
    ):
        """
        Run the service using uvicorn.

        Args:
            host: Host to bind to
            port: Port to bind to
            reload: Enable auto-reload for development
            log_level: Logging level
        """
        import uvicorn

        app = self.create_app()
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=reload,
            log_level=log_level,
        )


def create_app() -> FastAPI:
    """Factory function to create the FastAPI app (for uvicorn)."""
    service = ConversionService()
    return service.create_app()


# For direct execution: uvicorn healthcare_data_converter.service:app
app = create_app()
