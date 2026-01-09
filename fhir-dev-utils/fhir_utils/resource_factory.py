"""
Type-safe FHIR Resource Factory

Provides builder pattern classes for creating FHIR resources with
type safety, validation, and sensible defaults.
"""

import uuid
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Union, TypeVar, Generic
from enum import Enum

from fhir.resources.patient import Patient
from fhir.resources.condition import Condition
from fhir.resources.observation import Observation
from fhir.resources.medicationstatement import MedicationStatement
from fhir.resources.allergyintolerance import AllergyIntolerance
from fhir.resources.documentreference import DocumentReference
from fhir.resources.bundle import Bundle
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding
from fhir.resources.reference import Reference
from fhir.resources.humanname import HumanName
from fhir.resources.identifier import Identifier
from fhir.resources.attachment import Attachment
from fhir.resources.quantity import Quantity


def _generate_id(prefix: str = "fhir-dev") -> str:
    """Generate a unique ID with prefix."""
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


class ResourceStatus(Enum):
    """Common FHIR resource statuses."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    RESOLVED = "resolved"
    CONFIRMED = "confirmed"
    PRELIMINARY = "preliminary"
    FINAL = "final"


T = TypeVar("T")


class BaseBuilder(Generic[T]):
    """Base builder class with common functionality."""

    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._id = _generate_id()

    def with_id(self, id_value: str) -> "BaseBuilder[T]":
        """Set custom resource ID."""
        self._id = id_value
        return self

    def with_meta(self, profile: Optional[str] = None,
                  version_id: Optional[str] = None) -> "BaseBuilder[T]":
        """Add meta information."""
        meta = {}
        if profile:
            meta["profile"] = [profile]
        if version_id:
            meta["versionId"] = version_id
        if meta:
            self._data["meta"] = meta
        return self

    def build(self) -> T:
        """Build and validate the resource."""
        raise NotImplementedError

    def _create_codeable_concept(
        self,
        code: str,
        system: str,
        display: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a CodeableConcept structure."""
        coding = {"code": code, "system": system}
        if display:
            coding["display"] = display
        return {"coding": [coding], "text": display or code}

    def _create_reference(
        self,
        resource_type: str,
        resource_id: str,
        display: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a Reference structure."""
        ref = {"reference": f"{resource_type}/{resource_id}"}
        if display:
            ref["display"] = display
        return ref


class PatientBuilder(BaseBuilder[Patient]):
    """Builder for Patient resources with type-safe methods."""

    def __init__(self):
        super().__init__()
        self._data["resourceType"] = "Patient"

    def with_name(
        self,
        family: str,
        given: Optional[List[str]] = None,
        prefix: Optional[List[str]] = None,
        suffix: Optional[List[str]] = None,
        use: str = "official"
    ) -> "PatientBuilder":
        """Add patient name."""
        name = {"family": family, "use": use}
        if given:
            name["given"] = given
        if prefix:
            name["prefix"] = prefix
        if suffix:
            name["suffix"] = suffix

        if "name" not in self._data:
            self._data["name"] = []
        self._data["name"].append(name)
        return self

    def with_birth_date(self, birth_date: Union[str, date]) -> "PatientBuilder":
        """Set birth date."""
        if isinstance(birth_date, date):
            birth_date = birth_date.isoformat()
        self._data["birthDate"] = birth_date
        return self

    def with_gender(self, gender: str) -> "PatientBuilder":
        """Set gender (male, female, other, unknown)."""
        valid_genders = ["male", "female", "other", "unknown"]
        if gender.lower() not in valid_genders:
            raise ValueError(f"Gender must be one of: {valid_genders}")
        self._data["gender"] = gender.lower()
        return self

    def with_identifier(
        self,
        value: str,
        system: Optional[str] = None,
        type_code: Optional[str] = None
    ) -> "PatientBuilder":
        """Add identifier (MRN, SSN, etc.)."""
        identifier = {"value": value}
        if system:
            identifier["system"] = system
        if type_code:
            identifier["type"] = self._create_codeable_concept(
                type_code,
                "http://terminology.hl7.org/CodeSystem/v2-0203"
            )

        if "identifier" not in self._data:
            self._data["identifier"] = []
        self._data["identifier"].append(identifier)
        return self

    def with_mrn(self, mrn: str, system: Optional[str] = None) -> "PatientBuilder":
        """Add Medical Record Number."""
        return self.with_identifier(mrn, system, "MR")

    def with_contact(
        self,
        phone: Optional[str] = None,
        email: Optional[str] = None
    ) -> "PatientBuilder":
        """Add contact information."""
        if "telecom" not in self._data:
            self._data["telecom"] = []

        if phone:
            self._data["telecom"].append({
                "system": "phone",
                "value": phone,
                "use": "home"
            })
        if email:
            self._data["telecom"].append({
                "system": "email",
                "value": email
            })
        return self

    def with_address(
        self,
        line: Optional[List[str]] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        postal_code: Optional[str] = None,
        country: Optional[str] = None
    ) -> "PatientBuilder":
        """Add address."""
        address = {"use": "home"}
        if line:
            address["line"] = line
        if city:
            address["city"] = city
        if state:
            address["state"] = state
        if postal_code:
            address["postalCode"] = postal_code
        if country:
            address["country"] = country

        if "address" not in self._data:
            self._data["address"] = []
        self._data["address"].append(address)
        return self

    def active(self, is_active: bool = True) -> "PatientBuilder":
        """Set active status."""
        self._data["active"] = is_active
        return self

    def build(self) -> Patient:
        """Build and validate Patient resource."""
        self._data["id"] = self._id
        return Patient(**self._data)


class ConditionBuilder(BaseBuilder[Condition]):
    """Builder for Condition resources."""

    def __init__(self):
        super().__init__()
        self._data["resourceType"] = "Condition"

    def for_patient(self, patient_id: str) -> "ConditionBuilder":
        """Set the subject patient reference."""
        self._data["subject"] = self._create_reference("Patient", patient_id)
        return self

    def with_code(
        self,
        code: str,
        system: str = "http://snomed.info/sct",
        display: Optional[str] = None
    ) -> "ConditionBuilder":
        """Set condition code (SNOMED CT, ICD-10, etc.)."""
        self._data["code"] = self._create_codeable_concept(code, system, display)
        return self

    def with_snomed(self, code: str, display: Optional[str] = None) -> "ConditionBuilder":
        """Set SNOMED CT code."""
        return self.with_code(code, "http://snomed.info/sct", display)

    def with_icd10(self, code: str, display: Optional[str] = None) -> "ConditionBuilder":
        """Set ICD-10 code."""
        return self.with_code(code, "http://hl7.org/fhir/sid/icd-10-cm", display)

    def with_clinical_status(
        self,
        status: str = "active"
    ) -> "ConditionBuilder":
        """Set clinical status (active, recurrence, relapse, inactive, remission, resolved)."""
        self._data["clinicalStatus"] = self._create_codeable_concept(
            status,
            "http://terminology.hl7.org/CodeSystem/condition-clinical",
            status.capitalize()
        )
        return self

    def with_verification_status(
        self,
        status: str = "confirmed"
    ) -> "ConditionBuilder":
        """Set verification status (unconfirmed, provisional, differential, confirmed, refuted)."""
        self._data["verificationStatus"] = self._create_codeable_concept(
            status,
            "http://terminology.hl7.org/CodeSystem/condition-ver-status",
            status.capitalize()
        )
        return self

    def with_category(
        self,
        category: str = "encounter-diagnosis"
    ) -> "ConditionBuilder":
        """Set category (problem-list-item, encounter-diagnosis)."""
        self._data["category"] = [self._create_codeable_concept(
            category,
            "http://terminology.hl7.org/CodeSystem/condition-category"
        )]
        return self

    def with_onset(
        self,
        onset_date: Union[str, date, datetime]
    ) -> "ConditionBuilder":
        """Set onset date."""
        if isinstance(onset_date, (date, datetime)):
            onset_date = onset_date.isoformat()
        self._data["onsetDateTime"] = onset_date
        return self

    def with_severity(
        self,
        severity: str,
        system: str = "http://snomed.info/sct"
    ) -> "ConditionBuilder":
        """Set severity (mild, moderate, severe)."""
        severity_codes = {
            "mild": ("255604002", "Mild"),
            "moderate": ("6736007", "Moderate"),
            "severe": ("24484000", "Severe")
        }
        code, display = severity_codes.get(severity.lower(), (severity, severity))
        self._data["severity"] = self._create_codeable_concept(code, system, display)
        return self

    def with_note(self, text: str) -> "ConditionBuilder":
        """Add a clinical note."""
        if "note" not in self._data:
            self._data["note"] = []
        self._data["note"].append({"text": text})
        return self

    def build(self) -> Condition:
        """Build and validate Condition resource."""
        self._data["id"] = self._id
        return Condition(**self._data)


class ObservationBuilder(BaseBuilder[Observation]):
    """Builder for Observation resources (vitals, labs, etc.)."""

    def __init__(self):
        super().__init__()
        self._data["resourceType"] = "Observation"
        self._data["status"] = "final"

    def for_patient(self, patient_id: str) -> "ObservationBuilder":
        """Set the subject patient reference."""
        self._data["subject"] = self._create_reference("Patient", patient_id)
        return self

    def with_code(
        self,
        code: str,
        system: str = "http://loinc.org",
        display: Optional[str] = None
    ) -> "ObservationBuilder":
        """Set observation code (LOINC recommended)."""
        self._data["code"] = self._create_codeable_concept(code, system, display)
        return self

    def with_loinc(self, code: str, display: Optional[str] = None) -> "ObservationBuilder":
        """Set LOINC code."""
        return self.with_code(code, "http://loinc.org", display)

    def with_value_quantity(
        self,
        value: float,
        unit: str,
        system: str = "http://unitsofmeasure.org",
        code: Optional[str] = None
    ) -> "ObservationBuilder":
        """Set numeric value with unit."""
        self._data["valueQuantity"] = {
            "value": value,
            "unit": unit,
            "system": system,
            "code": code or unit
        }
        return self

    def with_value_string(self, value: str) -> "ObservationBuilder":
        """Set string value."""
        self._data["valueString"] = value
        return self

    def with_value_codeable_concept(
        self,
        code: str,
        system: str,
        display: Optional[str] = None
    ) -> "ObservationBuilder":
        """Set coded value."""
        self._data["valueCodeableConcept"] = self._create_codeable_concept(
            code, system, display
        )
        return self

    def with_status(self, status: str = "final") -> "ObservationBuilder":
        """Set observation status."""
        self._data["status"] = status
        return self

    def with_category(
        self,
        category: str = "vital-signs"
    ) -> "ObservationBuilder":
        """Set category (vital-signs, laboratory, etc.)."""
        self._data["category"] = [self._create_codeable_concept(
            category,
            "http://terminology.hl7.org/CodeSystem/observation-category"
        )]
        return self

    def with_effective_datetime(
        self,
        effective_dt: Union[str, datetime]
    ) -> "ObservationBuilder":
        """Set effective datetime."""
        if isinstance(effective_dt, datetime):
            effective_dt = effective_dt.isoformat()
        self._data["effectiveDateTime"] = effective_dt
        return self

    def with_reference_range(
        self,
        low: Optional[float] = None,
        high: Optional[float] = None,
        unit: Optional[str] = None,
        text: Optional[str] = None
    ) -> "ObservationBuilder":
        """Add reference range."""
        range_data = {}
        if low is not None:
            range_data["low"] = {"value": low}
            if unit:
                range_data["low"]["unit"] = unit
        if high is not None:
            range_data["high"] = {"value": high}
            if unit:
                range_data["high"]["unit"] = unit
        if text:
            range_data["text"] = text

        if "referenceRange" not in self._data:
            self._data["referenceRange"] = []
        self._data["referenceRange"].append(range_data)
        return self

    def with_interpretation(
        self,
        interpretation: str
    ) -> "ObservationBuilder":
        """Set interpretation (N=normal, H=high, L=low, etc.)."""
        interpretations = {
            "N": ("N", "Normal"),
            "H": ("H", "High"),
            "L": ("L", "Low"),
            "HH": ("HH", "Critical High"),
            "LL": ("LL", "Critical Low"),
            "A": ("A", "Abnormal")
        }
        code, display = interpretations.get(interpretation.upper(), (interpretation, interpretation))
        self._data["interpretation"] = [self._create_codeable_concept(
            code,
            "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
            display
        )]
        return self

    def build(self) -> Observation:
        """Build and validate Observation resource."""
        self._data["id"] = self._id
        return Observation(**self._data)


class MedicationStatementBuilder(BaseBuilder[MedicationStatement]):
    """Builder for MedicationStatement resources."""

    def __init__(self):
        super().__init__()
        self._data["resourceType"] = "MedicationStatement"
        self._data["status"] = "active"

    def for_patient(self, patient_id: str) -> "MedicationStatementBuilder":
        """Set the subject patient reference."""
        self._data["subject"] = self._create_reference("Patient", patient_id)
        return self

    def with_medication_code(
        self,
        code: str,
        system: str = "http://www.nlm.nih.gov/research/umls/rxnorm",
        display: Optional[str] = None
    ) -> "MedicationStatementBuilder":
        """Set medication code (RxNorm recommended)."""
        self._data["medicationCodeableConcept"] = self._create_codeable_concept(
            code, system, display
        )
        return self

    def with_rxnorm(self, code: str, display: Optional[str] = None) -> "MedicationStatementBuilder":
        """Set RxNorm code."""
        return self.with_medication_code(
            code,
            "http://www.nlm.nih.gov/research/umls/rxnorm",
            display
        )

    def with_status(self, status: str = "active") -> "MedicationStatementBuilder":
        """Set status (active, completed, entered-in-error, intended, stopped, on-hold)."""
        self._data["status"] = status
        return self

    def with_effective_period(
        self,
        start: Union[str, date, datetime],
        end: Optional[Union[str, date, datetime]] = None
    ) -> "MedicationStatementBuilder":
        """Set effective period."""
        if isinstance(start, (date, datetime)):
            start = start.isoformat()
        period = {"start": start}
        if end:
            if isinstance(end, (date, datetime)):
                end = end.isoformat()
            period["end"] = end
        self._data["effectivePeriod"] = period
        return self

    def with_dosage(
        self,
        text: str,
        route: Optional[str] = None,
        route_display: Optional[str] = None,
        dose_value: Optional[float] = None,
        dose_unit: Optional[str] = None,
        frequency: Optional[str] = None
    ) -> "MedicationStatementBuilder":
        """Add dosage information."""
        dosage = {"text": text}

        if route:
            dosage["route"] = self._create_codeable_concept(
                route,
                "http://snomed.info/sct",
                route_display or route
            )

        if dose_value is not None and dose_unit:
            dosage["doseAndRate"] = [{
                "doseQuantity": {
                    "value": dose_value,
                    "unit": dose_unit,
                    "system": "http://unitsofmeasure.org"
                }
            }]

        if "dosage" not in self._data:
            self._data["dosage"] = []
        self._data["dosage"].append(dosage)
        return self

    def with_reason(
        self,
        code: str,
        system: str = "http://snomed.info/sct",
        display: Optional[str] = None
    ) -> "MedicationStatementBuilder":
        """Add reason for medication."""
        if "reasonCode" not in self._data:
            self._data["reasonCode"] = []
        self._data["reasonCode"].append(
            self._create_codeable_concept(code, system, display)
        )
        return self

    def build(self) -> MedicationStatement:
        """Build and validate MedicationStatement resource."""
        self._data["id"] = self._id
        return MedicationStatement(**self._data)


class AllergyIntoleranceBuilder(BaseBuilder[AllergyIntolerance]):
    """Builder for AllergyIntolerance resources."""

    def __init__(self):
        super().__init__()
        self._data["resourceType"] = "AllergyIntolerance"

    def for_patient(self, patient_id: str) -> "AllergyIntoleranceBuilder":
        """Set the patient reference."""
        self._data["patient"] = self._create_reference("Patient", patient_id)
        return self

    def with_code(
        self,
        code: str,
        system: str = "http://snomed.info/sct",
        display: Optional[str] = None
    ) -> "AllergyIntoleranceBuilder":
        """Set allergy code."""
        self._data["code"] = self._create_codeable_concept(code, system, display)
        return self

    def with_clinical_status(
        self,
        status: str = "active"
    ) -> "AllergyIntoleranceBuilder":
        """Set clinical status (active, inactive, resolved)."""
        self._data["clinicalStatus"] = self._create_codeable_concept(
            status,
            "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical"
        )
        return self

    def with_verification_status(
        self,
        status: str = "confirmed"
    ) -> "AllergyIntoleranceBuilder":
        """Set verification status."""
        self._data["verificationStatus"] = self._create_codeable_concept(
            status,
            "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification"
        )
        return self

    def with_type(self, allergy_type: str = "allergy") -> "AllergyIntoleranceBuilder":
        """Set type (allergy, intolerance)."""
        self._data["type"] = allergy_type
        return self

    def with_category(
        self,
        category: str
    ) -> "AllergyIntoleranceBuilder":
        """Add category (food, medication, environment, biologic)."""
        if "category" not in self._data:
            self._data["category"] = []
        self._data["category"].append(category)
        return self

    def with_criticality(
        self,
        criticality: str = "low"
    ) -> "AllergyIntoleranceBuilder":
        """Set criticality (low, high, unable-to-assess)."""
        self._data["criticality"] = criticality
        return self

    def with_reaction(
        self,
        manifestation_code: str,
        manifestation_display: str,
        severity: Optional[str] = None,
        description: Optional[str] = None
    ) -> "AllergyIntoleranceBuilder":
        """Add reaction information."""
        reaction = {
            "manifestation": [self._create_codeable_concept(
                manifestation_code,
                "http://snomed.info/sct",
                manifestation_display
            )]
        }
        if severity:
            reaction["severity"] = severity
        if description:
            reaction["description"] = description

        if "reaction" not in self._data:
            self._data["reaction"] = []
        self._data["reaction"].append(reaction)
        return self

    def with_onset(
        self,
        onset_date: Union[str, date, datetime]
    ) -> "AllergyIntoleranceBuilder":
        """Set onset date."""
        if isinstance(onset_date, (date, datetime)):
            onset_date = onset_date.isoformat()
        self._data["onsetDateTime"] = onset_date
        return self

    def build(self) -> AllergyIntolerance:
        """Build and validate AllergyIntolerance resource."""
        self._data["id"] = self._id
        return AllergyIntolerance(**self._data)


class DocumentReferenceBuilder(BaseBuilder[DocumentReference]):
    """Builder for DocumentReference resources."""

    def __init__(self):
        super().__init__()
        self._data["resourceType"] = "DocumentReference"
        self._data["status"] = "current"

    def for_patient(self, patient_id: str) -> "DocumentReferenceBuilder":
        """Set the subject patient reference."""
        self._data["subject"] = self._create_reference("Patient", patient_id)
        return self

    def with_type(
        self,
        code: str,
        system: str = "http://loinc.org",
        display: Optional[str] = None
    ) -> "DocumentReferenceBuilder":
        """Set document type code."""
        self._data["type"] = self._create_codeable_concept(code, system, display)
        return self

    def with_category(
        self,
        code: str,
        system: str = "http://loinc.org",
        display: Optional[str] = None
    ) -> "DocumentReferenceBuilder":
        """Add document category."""
        if "category" not in self._data:
            self._data["category"] = []
        self._data["category"].append(
            self._create_codeable_concept(code, system, display)
        )
        return self

    def with_status(self, status: str = "current") -> "DocumentReferenceBuilder":
        """Set status (current, superseded, entered-in-error)."""
        self._data["status"] = status
        return self

    def with_date(
        self,
        doc_date: Union[str, datetime]
    ) -> "DocumentReferenceBuilder":
        """Set document date."""
        if isinstance(doc_date, datetime):
            doc_date = doc_date.isoformat()
        self._data["date"] = doc_date
        return self

    def with_content(
        self,
        data: Optional[str] = None,
        url: Optional[str] = None,
        content_type: str = "text/plain",
        title: Optional[str] = None
    ) -> "DocumentReferenceBuilder":
        """Add document content."""
        import base64

        attachment = {"contentType": content_type}
        if data:
            attachment["data"] = base64.b64encode(data.encode()).decode()
        if url:
            attachment["url"] = url
        if title:
            attachment["title"] = title

        content = {"attachment": attachment}

        if "content" not in self._data:
            self._data["content"] = []
        self._data["content"].append(content)
        return self

    def with_author(
        self,
        practitioner_id: Optional[str] = None,
        organization_id: Optional[str] = None
    ) -> "DocumentReferenceBuilder":
        """Add author reference."""
        if "author" not in self._data:
            self._data["author"] = []

        if practitioner_id:
            self._data["author"].append(
                self._create_reference("Practitioner", practitioner_id)
            )
        if organization_id:
            self._data["author"].append(
                self._create_reference("Organization", organization_id)
            )
        return self

    def with_description(self, description: str) -> "DocumentReferenceBuilder":
        """Set document description."""
        self._data["description"] = description
        return self

    def build(self) -> DocumentReference:
        """Build and validate DocumentReference resource."""
        self._data["id"] = self._id
        return DocumentReference(**self._data)


class ResourceFactory:
    """
    Factory class providing convenient access to all resource builders.

    Example:
        factory = ResourceFactory()
        patient = factory.patient() \\
            .with_name("Doe", given=["John"]) \\
            .with_birth_date("1990-01-15") \\
            .with_gender("male") \\
            .build()
    """

    @staticmethod
    def patient() -> PatientBuilder:
        """Create a new Patient builder."""
        return PatientBuilder()

    @staticmethod
    def condition() -> ConditionBuilder:
        """Create a new Condition builder."""
        return ConditionBuilder()

    @staticmethod
    def observation() -> ObservationBuilder:
        """Create a new Observation builder."""
        return ObservationBuilder()

    @staticmethod
    def medication_statement() -> MedicationStatementBuilder:
        """Create a new MedicationStatement builder."""
        return MedicationStatementBuilder()

    @staticmethod
    def allergy_intolerance() -> AllergyIntoleranceBuilder:
        """Create a new AllergyIntolerance builder."""
        return AllergyIntoleranceBuilder()

    @staticmethod
    def document_reference() -> DocumentReferenceBuilder:
        """Create a new DocumentReference builder."""
        return DocumentReferenceBuilder()
