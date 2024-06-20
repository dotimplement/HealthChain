from pydantic import BaseModel, Field
from typing import List, Literal

from healthchain.fhir_resources.primitives import (
    stringModel,
    idModel,
    uriModel,
    codeModel,
    dateTimeModel,
    canonicalModel,
)
from healthchain.fhir_resources.generalpurpose import (
    Extension,
    Identifier,
    CodeableConcept,
    Reference,
    Period,
    CodeableReference,
    Narrative,
    Age,
    Range,
    Meta,
    Timing,
)


class ProcedurePerformer(BaseModel):
    id_field: stringModel = Field(
        default=None,
        alias="id",
        description="Unique id for the element within a resource (for internal references). This may be any string value that does not contain spaces.",
    )
    extension_field: List[Extension] = Field(
        default=None,
        alias="extension",
        description="May be used to represent additional information that is not part of the basic definition of the element. To make the use of extensions safe and managable, there is a strict set of governance applied to the definition and use of extensions. Though any implementer can define an extension, there is a set of requirements that SHALL be met as part of the definition of the extension.",
    )
    modifierExtension_field: List[Extension] = Field(
        default=None,
        alias="modifierExtension",
        description="May be used to represent additional information that is not part of the basic definition of the element and that modifies the understanding of the element in which it is contained and/or the understanding of the containing element's descendants. Usually modifier elements provide negation or qualification. To make the use of extensions safe and managable, there is a strict set of governance applied to the definition and use of extensions. Though any implementer can define an extension, there is a set of requirements that SHALL be met as part of the definition of the extension. Applications processing a resource are required to check for modifier extensions.",
    )
    function_field: CodeableConcept = Field(
        default=None,
        alias="function",
        description="Distinguishes the type of involvement of the performer in the procedure. For example, surgeon, anaesthetist, endoscopist.",
    )
    actor_field: Reference = Field(
        default=None,
        alias="actor",
        description="Indicates who or what performed the procedure.",
    )
    onBehalfOf_field: Reference = Field(
        default=None,
        alias="onBehalfOf",
        description="The Organization the Patient, RelatedPerson, Device, CareTeam, and HealthcareService was acting on behalf of.",
    )
    period_field: Period = Field(
        default=None,
        alias="period",
        description="Time period during which the performer performed the procedure.",
    )


class ProcedureFocalDevice(BaseModel):
    id_field: stringModel = Field(
        default=None,
        alias="id",
        description="Unique id for the element within a resource (for internal references). This may be any string value that does not contain spaces.",
    )
    extension_field: List[Extension] = Field(
        default=None,
        alias="extension",
        description="May be used to represent additional information that is not part of the basic definition of the element. To make the use of extensions safe and managable, there is a strict set of governance applied to the definition and use of extensions. Though any implementer can define an extension, there is a set of requirements that SHALL be met as part of the definition of the extension.",
    )
    modifierExtension_field: List[Extension] = Field(
        default=None,
        alias="modifierExtension",
        description="May be used to represent additional information that is not part of the basic definition of the element and that modifies the understanding of the element in which it is contained and/or the understanding of the containing element's descendants. Usually modifier elements provide negation or qualification. To make the use of extensions safe and managable, there is a strict set of governance applied to the definition and use of extensions. Though any implementer can define an extension, there is a set of requirements that SHALL be met as part of the definition of the extension. Applications processing a resource are required to check for modifier extensions.",
    )
    action_field: CodeableConcept = Field(
        default=None,
        alias="action",
        description="The kind of change that happened to the device during the procedure.",
    )
    manipulated_field: Reference = Field(
        default=None,
        alias="manipulated",
        description="The device that was manipulated (changed) during the procedure.",
    )


class Procedure(BaseModel):
    resourceType: Literal["Procedure"] = "Procedure"
    id_field: idModel = Field(
        default=None,
        alias="id",
        description="The logical id of the resource, as used in the URL for the resource. Once assigned, this value never changes.",
    )
    meta_field: Meta = Field(
        default=None,
        alias="meta",
        description="The metadata about the resource. This is content that is maintained by the infrastructure. Changes to the content might not always be associated with version changes to the resource.",
    )
    implicitRules_field: uriModel = Field(
        default=None,
        alias="implicitRules",
        description="A reference to a set of rules that were followed when the resource was constructed, and which must be understood when processing the content. Often, this is a reference to an implementation guide that defines the special rules along with other profiles etc.",
    )
    language_field: codeModel = Field(
        default=None,
        alias="language",
        description="The base language in which the resource is written.",
    )
    text_field: Narrative = Field(
        default=None,
        alias="text",
        description="A human-readable narrative that contains a summary of the resource and can be used to represent the content of the resource to a human. The narrative need not encode all the structured data, but is required to contain sufficient detail to make it clinically safe for a human to just read the narrative. Resource definitions may define what content should be represented in the narrative to ensure clinical safety.",
    )
    # contained_field: List[ResourceListModel] = Field(
    #     default=None,
    #     alias="contained",
    #     description="These resources do not have an independent existence apart from the resource that contains them - they cannot be identified independently, nor can they have their own independent transaction scope. This is allowed to be a Parameters resource if and only if it is referenced by a resource that provides context/meaning.",
    # )
    extension_field: List[Extension] = Field(
        default=None,
        alias="extension",
        description="May be used to represent additional information that is not part of the basic definition of the resource. To make the use of extensions safe and managable, there is a strict set of governance applied to the definition and use of extensions. Though any implementer can define an extension, there is a set of requirements that SHALL be met as part of the definition of the extension.",
    )
    modifierExtension_field: List[Extension] = Field(
        default=None,
        alias="modifierExtension",
        description="May be used to represent additional information that is not part of the basic definition of the resource and that modifies the understanding of the element that contains it and/or the understanding of the containing element's descendants. Usually modifier elements provide negation or qualification. To make the use of extensions safe and managable, there is a strict set of governance applied to the definition and use of extensions. Though any implementer is allowed to define an extension, there is a set of requirements that SHALL be met as part of the definition of the extension. Applications processing a resource are required to check for modifier extensions.",
    )
    identifier_field: List[Identifier] = Field(
        default=None,
        alias="identifier",
        description="Business identifiers assigned to this procedure by the performer or other systems which remain constant as the resource is updated and is propagated from server to server.",
    )
    instantiatesCanonical_field: List[canonicalModel] = Field(
        default=None,
        alias="instantiatesCanonical",
        description="The URL pointing to a FHIR-defined protocol, guideline, order set or other definition that is adhered to in whole or in part by this Procedure.",
    )
    instantiatesUri_field: List[uriModel] = Field(
        default=None,
        alias="instantiatesUri",
        description="The URL pointing to an externally maintained protocol, guideline, order set or other definition that is adhered to in whole or in part by this Procedure.",
    )
    basedOn_field: List[Reference] = Field(
        default=None,
        alias="basedOn",
        description="A reference to a resource that contains details of the request for this procedure.",
    )
    partOf_field: List[Reference] = Field(
        default=None,
        alias="partOf",
        description="A larger event of which this particular procedure is a component or step.",
    )
    status_field: codeModel = Field(
        default=None,
        alias="status",
        description="A code specifying the state of the procedure. Generally, this will be the in-progress or completed state.",
    )
    statusReason_field: CodeableConcept = Field(
        default=None,
        alias="statusReason",
        description="Captures the reason for the current state of the procedure.",
    )
    category_field: List[CodeableConcept] = Field(
        default=None,
        alias="category",
        description="A code that classifies the procedure for searching, sorting and display purposes (e.g. Surgical Procedure).",
    )
    code_field: CodeableConcept = Field(
        default=None,
        alias="code",
        description="The specific procedure that is performed. Use text if the exact nature of the procedure cannot be coded (e.g. Laparoscopic Appendectomy).",
    )
    subject_field: Reference = Field(
        default=None,
        alias="subject",
        description="On whom or on what the procedure was performed. This is usually an individual human, but can also be performed on animals, groups of humans or animals, organizations or practitioners (for licensing), locations or devices (for safety inspections or regulatory authorizations).  If the actual focus of the procedure is different from the subject, the focus element specifies the actual focus of the procedure.",
    )
    focus_field: Reference = Field(
        default=None,
        alias="focus",
        description="Who is the target of the procedure when it is not the subject of record only.  If focus is not present, then subject is the focus.  If focus is present and the subject is one of the targets of the procedure, include subject as a focus as well. If focus is present and the subject is not included in focus, it implies that the procedure was only targeted on the focus. For example, when a caregiver is given education for a patient, the caregiver would be the focus and the procedure record is associated with the subject (e.g. patient).  For example, use focus when recording the target of the education, training, or counseling is the parent or relative of a patient.",
    )
    encounter_field: Reference = Field(
        default=None,
        alias="encounter",
        description="The Encounter during which this Procedure was created or performed or to which the creation of this record is tightly associated.",
    )
    occurrencePeriod_field: Period = Field(
        default=None,
        alias="occurrencePeriod",
        description="Estimated or actual date, date-time, period, or age when the procedure did occur or is occurring.  Allows a period to support complex procedures that span more than one date, and also allows for the length of the procedure to be captured.",
    )
    occurrenceAge_field: Age = Field(
        default=None,
        alias="occurrenceAge",
        description="Estimated or actual date, date-time, period, or age when the procedure did occur or is occurring.  Allows a period to support complex procedures that span more than one date, and also allows for the length of the procedure to be captured.",
    )
    occurrenceRange_field: Range = Field(
        default=None,
        alias="occurrenceRange",
        description="Estimated or actual date, date-time, period, or age when the procedure did occur or is occurring.  Allows a period to support complex procedures that span more than one date, and also allows for the length of the procedure to be captured.",
    )
    occurrenceTiming_field: Timing = Field(
        default=None,
        alias="occurrenceTiming",
        description="Estimated or actual date, date-time, period, or age when the procedure did occur or is occurring.  Allows a period to support complex procedures that span more than one date, and also allows for the length of the procedure to be captured.",
    )
    recorded_field: dateTimeModel = Field(
        default=None,
        alias="recorded",
        description="The date the occurrence of the procedure was first captured in the record regardless of Procedure.status (potentially after the occurrence of the event).",
    )
    recorder_field: Reference = Field(
        default=None,
        alias="recorder",
        description="Individual who recorded the record and takes responsibility for its content.",
    )
    reportedReference_field: Reference = Field(
        default=None,
        alias="reportedReference",
        description="Indicates if this record was captured as a secondary 'reported' record rather than as an original primary source-of-truth record.  It may also indicate the source of the report.",
    )
    performer_field: List[ProcedurePerformer] = Field(
        default=None,
        alias="performer",
        description="Indicates who or what performed the procedure and how they were involved.",
    )
    location_field: Reference = Field(
        default=None,
        alias="location",
        description="The location where the procedure actually happened.  E.g. a newborn at home, a tracheostomy at a restaurant.",
    )
    reason_field: List[CodeableReference] = Field(
        default=None,
        alias="reason",
        description="The coded reason or reference why the procedure was performed. This may be a coded entity of some type, be present as text, or be a reference to one of several resources that justify the procedure.",
    )
    bodySite_field: List[CodeableConcept] = Field(
        default=None,
        alias="bodySite",
        description="Detailed and structured anatomical location information. Multiple locations are allowed - e.g. multiple punch biopsies of a lesion.",
    )
    outcome_field: CodeableConcept = Field(
        default=None,
        alias="outcome",
        description="The outcome of the procedure - did it resolve the reasons for the procedure being performed?",
    )
    report_field: List[Reference] = Field(
        default=None,
        alias="report",
        description="This could be a histology result, pathology report, surgical report, etc.",
    )
    complication_field: List[CodeableReference] = Field(
        default=None,
        alias="complication",
        description="Any complications that occurred during the procedure, or in the immediate post-performance period. These are generally tracked separately from the notes, which will typically describe the procedure itself rather than any 'post procedure' issues.",
    )
    followUp_field: List[CodeableConcept] = Field(
        default=None,
        alias="followUp",
        description="If the procedure required specific follow up - e.g. removal of sutures. The follow up may be represented as a simple note or could potentially be more complex, in which case the CarePlan resource can be used.",
    )
    # note_field: List[AnnotationModel] = Field(
    #     default=None,
    #     alias="note",
    #     description="Any other notes and comments about the procedure.",
    # )
    focalDevice_field: List[ProcedureFocalDevice] = Field(
        default=None,
        alias="focalDevice",
        description="A device that is implanted, removed or otherwise manipulated (calibration, battery replacement, fitting a prosthesis, attaching a wound-vac, etc.) as a focal portion of the Procedure.",
    )
    used_field: List[CodeableReference] = Field(
        default=None,
        alias="used",
        description="Identifies medications, devices and any other substance used as part of the procedure.",
    )
    supportingInfo_field: List[Reference] = Field(
        default=None,
        alias="supportingInfo",
        description="Other resources from the patient record that may be relevant to the procedure.  The information from these resources was either used to create the instance or is provided to help with its interpretation. This extension should not be used if more specific inline elements or extensions are available.",
    )
