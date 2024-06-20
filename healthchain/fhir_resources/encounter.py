from pydantic import BaseModel, Field
from typing import List, Literal

from healthchain.fhir_resources.primitives import (
    stringModel,
    idModel,
    uriModel,
    codeModel,
    dateTimeModel,
)
from healthchain.fhir_resources.generalpurpose import (
    Extension,
    Identifier,
    CodeableConcept,
    Reference,
    Period,
    CodeableReference,
    Narrative,
    Meta,
)


class EncounterParticipant(BaseModel):
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
    type_field: List[CodeableConcept] = Field(
        default=None,
        alias="type",
        description="Role of participant in encounter.",
    )
    period_field: Period = Field(
        default=None,
        alias="period",
        description="The period of time that the specified participant participated in the encounter. These can overlap or be sub-sets of the overall encounter's period.",
    )
    actor_field: Reference = Field(
        default=None,
        alias="actor",
        description="Person involved in the encounter, the patient/group is also included here to indicate that the patient was actually participating in the encounter. Not including the patient here covers use cases such as a case meeting between practitioners about a patient - non contact times.",
    )


class EncounterReason(BaseModel):
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
    use_field: List[CodeableConcept] = Field(
        default=None,
        alias="use",
        description="What the reason value should be used as e.g. Chief Complaint, Health Concern, Health Maintenance (including screening).",
    )
    value_field: List[CodeableReference] = Field(
        default=None,
        alias="value",
        description="Reason the encounter takes place, expressed as a code or a reference to another resource. For admissions, this can be used for a coded admission diagnosis.",
    )


class EncounterDiagnosis(BaseModel):
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
    condition_field: List[CodeableReference] = Field(
        default=None,
        alias="condition",
        description="The coded diagnosis or a reference to a Condition (with other resources referenced in the evidence.detail), the use property will indicate the purpose of this specific diagnosis.",
    )
    use_field: List[CodeableConcept] = Field(
        default=None,
        alias="use",
        description="Role that this diagnosis has within the encounter (e.g. admission, billing, discharge …).",
    )


class EncounterAdmission(BaseModel):
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
    preAdmissionIdentifier_field: Identifier = Field(
        default=None,
        alias="preAdmissionIdentifier",
        description="Pre-admission identifier.",
    )
    origin_field: Reference = Field(
        default=None,
        alias="origin",
        description="The location/organization from which the patient came before admission.",
    )
    admitSource_field: CodeableConcept = Field(
        default=None,
        alias="admitSource",
        description="From where patient was admitted (physician referral, transfer).",
    )
    reAdmission_field: CodeableConcept = Field(
        default=None,
        alias="reAdmission",
        description="Indicates that this encounter is directly related to a prior admission, often because the conditions addressed in the prior admission were not fully addressed.",
    )
    destination_field: Reference = Field(
        default=None,
        alias="destination",
        description="Location/organization to which the patient is discharged.",
    )
    dischargeDisposition_field: CodeableConcept = Field(
        default=None,
        alias="dischargeDisposition",
        description="Category or kind of location after discharge.",
    )


class EncounterLocation(BaseModel):
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
    location_field: Reference = Field(
        default=None,
        alias="location",
        description="The location where the encounter takes place.",
    )
    status_field: codeModel = Field(
        default=None,
        alias="status",
        description="The status of the participants' presence at the specified location during the period specified. If the participant is no longer at the location, then the period will have an end date/time.",
    )
    form_field: CodeableConcept = Field(
        default=None,
        alias="form",
        description="This will be used to specify the required levels (bed/ward/room/etc.) desired to be recorded to simplify either messaging or query.",
    )
    period_field: Period = Field(
        default=None,
        alias="period",
        description="Time period during which the patient was present at the location.",
    )


class Encounter(BaseModel):
    resourceType: Literal["Encounter"] = "Encounter"
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
    # contained_field: List[ResourceListModel] = Field(default=None, alias="contained", description="These resources do not have an independent existence apart from the resource that contains them - they cannot be identified independently, nor can they have their own independent transaction scope. This is allowed to be a Parameters resource if and only if it is referenced by a resource that provides context/meaning.")
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
        description="Identifier(s) by which this encounter is known.",
    )
    status_field: codeModel = Field(
        default=None,
        alias="status",
        description="The current state of the encounter (not the state of the patient within the encounter - that is subjectState).",
    )
    class_field: List[CodeableConcept] = Field(
        default=None,
        alias="class",
        description="Concepts representing classification of patient encounter such as ambulatory (outpatient), inpatient, emergency, home health or others due to local variations.",
    )
    priority_field: CodeableConcept = Field(
        default=None,
        alias="priority",
        description="Indicates the urgency of the encounter.",
    )
    type_field: List[CodeableConcept] = Field(
        default=None,
        alias="type",
        description="Specific type of encounter (e.g. e-mail consultation, surgical day-care, skilled nursing, rehabilitation).",
    )
    serviceType_field: List[CodeableReference] = Field(
        default=None,
        alias="serviceType",
        description="Broad categorization of the service that is to be provided (e.g. cardiology).",
    )
    subject_field: Reference = Field(
        default=None,
        alias="subject",
        description="The patient or group related to this encounter. In some use-cases the patient MAY not be present, such as a case meeting about a patient between several practitioners or a careteam.",
    )
    subjectStatus_field: CodeableConcept = Field(
        default=None,
        alias="subjectStatus",
        description="The subjectStatus value can be used to track the patient's status within the encounter. It details whether the patient has arrived or departed, has been triaged or is currently in a waiting status.",
    )
    episodeOfCare_field: List[Reference] = Field(
        default=None,
        alias="episodeOfCare",
        description="Where a specific encounter should be classified as a part of a specific episode(s) of care this field should be used. This association can facilitate grouping of related encounters together for a specific purpose, such as government reporting, issue tracking, association via a common problem.  The association is recorded on the encounter as these are typically created after the episode of care and grouped on entry rather than editing the episode of care to append another encounter to it (the episode of care could span years).",
    )
    basedOn_field: List[Reference] = Field(
        default=None,
        alias="basedOn",
        description="The request this encounter satisfies (e.g. incoming referral or procedure request).",
    )
    careTeam_field: List[Reference] = Field(
        default=None,
        alias="careTeam",
        description="The group(s) of individuals, organizations that are allocated to participate in this encounter. The participants backbone will record the actuals of when these individuals participated during the encounter.",
    )
    partOf_field: Reference = Field(
        default=None,
        alias="partOf",
        description="Another Encounter of which this encounter is a part of (administratively or in time).",
    )
    serviceProvider_field: Reference = Field(
        default=None,
        alias="serviceProvider",
        description="The organization that is primarily responsible for this Encounter's services. This MAY be the same as the organization on the Patient record, however it could be different, such as if the actor performing the services was from an external organization (which may be billed seperately) for an external consultation.  Refer to the colonoscopy example on the Encounter examples tab.",
    )
    participant_field: List[EncounterParticipant] = Field(
        default=None,
        alias="participant",
        description="The list of people responsible for providing the service.",
    )
    appointment_field: List[Reference] = Field(
        default=None,
        alias="appointment",
        description="The appointment that scheduled this encounter.",
    )
    # virtualService_field: List[VirtualServiceDetailModel] = Field(default=None, alias="virtualService", description="Connection details of a virtual service (e.g. conference call).")
    actualPeriod_field: Period = Field(
        default=None,
        alias="actualPeriod",
        description="The actual start and end time of the encounter.",
    )
    plannedStartDate_field: dateTimeModel = Field(
        default=None,
        alias="plannedStartDate",
        description="The planned start date/time (or admission date) of the encounter.",
    )
    plannedEndDate_field: dateTimeModel = Field(
        default=None,
        alias="plannedEndDate",
        description="The planned end date/time (or discharge date) of the encounter.",
    )
    # length_field: DurationModel = Field(default=None, alias="length", description="Actual quantity of time the encounter lasted. This excludes the time during leaves of absence.")
    reason_field: List[EncounterReason] = Field(
        default=None,
        alias="reason",
        description="The list of medical reasons that are expected to be addressed during the episode of care.",
    )
    diagnosis_field: List[EncounterDiagnosis] = Field(
        default=None,
        alias="diagnosis",
        description="The list of diagnosis relevant to this encounter.",
    )
    account_field: List[Reference] = Field(
        default=None,
        alias="account",
        description="The set of accounts that may be used for billing for this Encounter.",
    )
    dietPreference_field: List[CodeableConcept] = Field(
        default=None,
        alias="dietPreference",
        description="Diet preferences reported by the patient.",
    )
    specialArrangement_field: List[CodeableConcept] = Field(
        default=None,
        alias="specialArrangement",
        description="Any special requests that have been made for this encounter, such as the provision of specific equipment or other things.",
    )
    specialCourtesy_field: List[CodeableConcept] = Field(
        default=None,
        alias="specialCourtesy",
        description="Special courtesies that may be provided to the patient during the encounter (VIP, board member, professional courtesy).",
    )
    admission_field: EncounterAdmission = Field(
        default=None,
        alias="admission",
        description="Details about the stay during which a healthcare service is provided.",
    )
    location_field: List[EncounterLocation] = Field(
        default=None,
        alias="location",
        description="List of locations where  the patient has been during this encounter.",
    )
