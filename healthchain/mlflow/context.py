"""Healthcare-specific run context with FHIR Provenance support."""

import datetime
import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PatientContext(BaseModel):
    """Anonymized patient context for healthcare tracking.

    This model captures aggregate/anonymized patient information
    suitable for logging in experiment tracking systems without
    exposing PHI (Protected Health Information).

    Attributes:
        cohort: Description of the patient cohort (e.g., "ICU patients")
        age_range: Age range of patients (e.g., "18-65")
        sample_size: Number of patients in the cohort
        inclusion_criteria: List of inclusion criteria for the cohort
        exclusion_criteria: List of exclusion criteria for the cohort
    """

    cohort: str = Field(
        default="unspecified",
        description="Description of the patient cohort",
    )
    age_range: Optional[str] = Field(
        default=None,
        description="Age range of patients (e.g., '18-65')",
    )
    sample_size: Optional[int] = Field(
        default=None,
        description="Number of patients in the cohort",
    )
    inclusion_criteria: List[str] = Field(
        default_factory=list,
        description="List of inclusion criteria",
    )
    exclusion_criteria: List[str] = Field(
        default_factory=list,
        description="List of exclusion criteria",
    )


class HealthcareRunContext(BaseModel):
    """Healthcare-specific run context with FHIR Provenance support.

    This model captures healthcare metadata for ML experiment runs,
    including model information, patient context, and regulatory
    compliance data. It can generate FHIR Provenance resources
    for audit trails required in healthcare settings.

    Attributes:
        model_id: Unique identifier for the model
        version: Model version string
        patient_context: Optional anonymized patient context
        organization: Organization responsible for the model
        purpose: Purpose or use case for the model
        data_sources: List of data sources used
        regulatory_tags: Regulatory compliance tags (e.g., "HIPAA", "FDA")
        custom_metadata: Additional custom metadata

    Example:
        >>> context = HealthcareRunContext(
        ...     model_id="sepsis-predictor",
        ...     version="1.2.0",
        ...     patient_context=PatientContext(
        ...         cohort="ICU patients",
        ...         age_range="18-90",
        ...         sample_size=1000
        ...     ),
        ...     organization="Hospital AI Lab",
        ...     purpose="Early sepsis detection"
        ... )
        >>> provenance = context.to_fhir_provenance()
    """

    model_id: str = Field(
        ...,
        description="Unique identifier for the model",
    )
    version: str = Field(
        ...,
        description="Model version string",
    )
    patient_context: Optional[PatientContext] = Field(
        default=None,
        description="Optional anonymized patient context",
    )
    organization: Optional[str] = Field(
        default=None,
        description="Organization responsible for the model",
    )
    purpose: Optional[str] = Field(
        default=None,
        description="Purpose or use case for the model",
    )
    data_sources: List[str] = Field(
        default_factory=list,
        description="List of data sources used",
    )
    regulatory_tags: List[str] = Field(
        default_factory=list,
        description="Regulatory compliance tags",
    )
    custom_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional custom metadata",
    )
    recorded: Optional[datetime.datetime] = Field(
        default=None,
        description="Timestamp when the context was recorded",
    )

    def to_fhir_provenance(self) -> Optional[Any]:
        """Generate a FHIR Provenance resource for audit trails.

        Creates a FHIR R4 Provenance resource that documents the
        ML model execution for healthcare regulatory compliance.

        Returns:
            FHIR Provenance resource if fhir.resources is available,
            None otherwise

        Note:
            Requires fhir.resources package to be installed.
        """
        try:
            from fhir.resources.codeableconcept import CodeableConcept
            from fhir.resources.coding import Coding
            from fhir.resources.provenance import Provenance, ProvenanceAgent
            from fhir.resources.reference import Reference

            from healthchain.fhir.utilities import _generate_id
        except ImportError:
            logger.warning(
                "fhir.resources not available, cannot generate FHIR Provenance"
            )
            return None

        # Use recorded time or current time
        recorded_time = self.recorded or datetime.datetime.now(datetime.timezone.utc)

        # Build agent for the ML model
        agent = ProvenanceAgent(
            type=CodeableConcept(
                coding=[
                    Coding(
                        system="http://terminology.hl7.org/CodeSystem/provenance-participant-type",
                        code="performer",
                        display="Performer",
                    )
                ]
            ),
            who=Reference(
                display=f"ML Model: {self.model_id} v{self.version}",
            ),
        )

        # Build activity coding
        activity = CodeableConcept(
            coding=[
                Coding(
                    system="http://terminology.hl7.org/CodeSystem/v3-DataOperation",
                    code="DERIVE",
                    display="derive",
                )
            ],
            text=self.purpose or "ML model inference",
        )

        # Build reason if regulatory tags exist
        reason = None
        if self.regulatory_tags:
            reason = [
                CodeableConcept(
                    text=f"Regulatory compliance: {', '.join(self.regulatory_tags)}"
                )
            ]

        # Create Provenance resource
        provenance = Provenance(
            id=_generate_id(),
            recorded=recorded_time.isoformat(),
            activity=activity,
            agent=[agent],
            reason=reason,
        )

        # Add policy references for data sources
        if self.data_sources:
            provenance.policy = [
                f"urn:healthchain:datasource:{ds}" for ds in self.data_sources
            ]

        return provenance

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to a dictionary for logging.

        Returns:
            Dictionary representation of the context
        """
        result = {
            "model_id": self.model_id,
            "version": self.version,
            "organization": self.organization,
            "purpose": self.purpose,
            "data_sources": self.data_sources,
            "regulatory_tags": self.regulatory_tags,
        }

        if self.patient_context:
            result["patient_context"] = self.patient_context.model_dump()

        if self.custom_metadata:
            result["custom_metadata"] = self.custom_metadata

        if self.recorded:
            result["recorded"] = self.recorded.isoformat()

        return result

    @classmethod
    def from_model_config(
        cls,
        model_id: str,
        version: str,
        **kwargs: Any,
    ) -> "HealthcareRunContext":
        """Create a HealthcareRunContext from model configuration.

        Args:
            model_id: Unique identifier for the model
            version: Model version string
            **kwargs: Additional context parameters

        Returns:
            HealthcareRunContext instance
        """
        return cls(
            model_id=model_id,
            version=version,
            recorded=datetime.datetime.now(datetime.timezone.utc),
            **kwargs,
        )
