from pydantic import BaseModel, Field
from typing import List, Literal

from healthchain.fhir_resources.primitives import (
    stringModel,
    idModel,
    uriModel,
    codeModel,
    dateTimeModel,
    booleanModel,
    integerModel,
)
from healthchain.fhir_resources.generalpurpose import (
    Extension,
    Identifier,
    CodeableConcept,
    Reference,
    Period,
    CodeableReference,
    Narrative,
    Range,
    Ratio,
    Quantity,
    Meta,
)


# TODO: Implement RatioModel and TimingModel
class DosageDoseAndRate(BaseModel):
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
    type_field: CodeableConcept = Field(
        default=None,
        alias="type",
        description="The kind of dose or rate specified, for example, ordered or calculated.",
    )
    doseRange_field: Range = Field(
        default=None, alias="doseRange", description="Amount of medication per dose."
    )
    doseQuantity_field: Quantity = Field(
        default=None, alias="doseQuantity", description="Amount of medication per dose."
    )
    rateRatio_field: Ratio = Field(
        default=None,
        alias="rateRatio",
        description="Amount of medication per unit of time.",
    )
    rateRange_field: Range = Field(
        default=None,
        alias="rateRange",
        description="Amount of medication per unit of time.",
    )
    rateQuantity_field: Quantity = Field(
        default=None,
        alias="rateQuantity",
        description="Amount of medication per unit of time.",
    )


class Dosage(BaseModel):
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
    sequence_field: integerModel = Field(
        default=None,
        alias="sequence",
        description="Indicates the order in which the dosage instructions should be applied or interpreted.",
    )
    text_field: stringModel = Field(
        default=None,
        alias="text",
        description="Free text dosage instructions e.g. SIG.",
    )
    additionalInstruction_field: List[CodeableConcept] = Field(
        default=None,
        alias="additionalInstruction",
        description="Supplemental instructions to the patient on how to take the medication  (e.g. with meals ortake half to one hour before food) or warnings for the patient about the medication (e.g. may cause drowsiness or avoid exposure of skin to direct sunlight or sunlamps).",
    )
    patientInstruction_field: stringModel = Field(
        default=None,
        alias="patientInstruction",
        description="Instructions in terms that are understood by the patient or consumer.",
    )
    # timing_field: TimingModel = Field(
    #     default=None,
    #     alias="timing",
    #     description="When medication should be administered.",
    # )
    asNeeded_field: booleanModel = Field(
        default=None,
        alias="asNeeded",
        description="Indicates whether the Medication is only taken when needed within a specific dosing schedule (Boolean option).",
    )
    asNeededFor_field: List[CodeableConcept] = Field(
        default=None,
        alias="asNeededFor",
        description="Indicates whether the Medication is only taken based on a precondition for taking the Medication (CodeableConcept).",
    )
    site_field: CodeableConcept = Field(
        default=None, alias="site", description="Body site to administer to."
    )
    route_field: CodeableConcept = Field(
        default=None, alias="route", description="How drug should enter body."
    )
    method_field: CodeableConcept = Field(
        default=None,
        alias="method",
        description="Technique for administering medication.",
    )
    doseAndRate_field: List[DosageDoseAndRate] = Field(
        default=None,
        alias="doseAndRate",
        description="Depending on the resource,this is the amount of medication administered, to  be administered or typical amount to be administered.",
    )
    maxDosePerPeriod_field: List[Ratio] = Field(
        default=None,
        alias="maxDosePerPeriod",
        description="Upper limit on medication per unit of time.",
    )
    maxDosePerAdministration_field: Quantity = Field(
        default=None,
        alias="maxDosePerAdministration",
        description="Upper limit on medication per administration.",
    )
    maxDosePerLifetime_field: Quantity = Field(
        default=None,
        alias="maxDosePerLifetime",
        description="Upper limit on medication per lifetime of the patient.",
    )


class Medication(BaseModel):
    code_field: CodeableConcept = Field(
        default=None, alias="code", description="Identifies the item being prescribed."
    )


class MedicationRequest(BaseModel):
    resourceType: Literal["MedicationRequest"] = "MedicationRequest"
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
    contained_field: List[Medication] = Field(
        default=None,
        alias="contained",
        description="These resources do not have an independent existence apart from the resource that contains them - they cannot be identified independently, nor can they have their own independent transaction scope. This is allowed to be a Parameters resource if and only if it is referenced by a resource that provides context/meaning.",
    )
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
        description="Identifiers associated with this medication request that are defined by business processes and/or used to refer to it when a direct URL reference to the resource itself is not appropriate. They are business identifiers assigned to this resource by the performer or other systems and remain constant as the resource is updated and propagates from server to server.",
    )
    basedOn_field: List[Reference] = Field(
        default=None,
        alias="basedOn",
        description="A plan or request that is fulfilled in whole or in part by this medication request.",
    )
    priorPrescription_field: Reference = Field(
        default=None,
        alias="priorPrescription",
        description="Reference to an order/prescription that is being replaced by this MedicationRequest.",
    )
    groupIdentifier_field: Identifier = Field(
        default=None,
        alias="groupIdentifier",
        description="A shared identifier common to multiple independent Request instances that were activated/authorized more or less simultaneously by a single author.  The presence of the same identifier on each request ties those requests together and may have business ramifications in terms of reporting of results, billing, etc.  E.g. a requisition number shared by a set of lab tests ordered together, or a prescription number shared by all meds ordered at one time.",
    )
    status_field: codeModel = Field(
        default=None,
        alias="status",
        description="A code specifying the current state of the order.  Generally, this will be active or completed state.",
    )
    statusReason_field: CodeableConcept = Field(
        default=None,
        alias="statusReason",
        description="Captures the reason for the current state of the MedicationRequest.",
    )
    statusChanged_field: dateTimeModel = Field(
        default=None,
        alias="statusChanged",
        description="The date (and perhaps time) when the status was changed.",
    )
    intent_field: codeModel = Field(
        default=None,
        alias="intent",
        description="Whether the request is a proposal, plan, or an original order.",
    )
    category_field: List[CodeableConcept] = Field(
        default=None,
        alias="category",
        description="An arbitrary categorization or grouping of the medication request.  It could be used for indicating where meds are intended to be administered, eg. in an inpatient setting or in a patient's home, or a legal category of the medication.",
    )
    priority_field: codeModel = Field(
        default=None,
        alias="priority",
        description="Indicates how quickly the Medication Request should be addressed with respect to other requests.",
    )
    doNotPerform_field: booleanModel = Field(
        default=None,
        alias="doNotPerform",
        description="If true, indicates that the provider is asking for the patient to either stop taking or to not start taking the specified medication. For example, the patient is taking an existing medication and the provider is changing their medication. They want to create two seperate requests: one to stop using the current medication and another to start the new medication.",
    )
    medication_field: CodeableReference = Field(
        default=None,
        alias="medication",
        description="Identifies the medication being requested. This is a link to a resource that represents the medication which may be the details of the medication or simply an attribute carrying a code that identifies the medication from a known list of medications.",
    )
    subject_field: Reference = Field(
        default=None,
        alias="subject",
        description="The individual or group for whom the medication has been requested.",
    )
    informationSource_field: List[Reference] = Field(
        default=None,
        alias="informationSource",
        description="The person or organization who provided the information about this request, if the source is someone other than the requestor.  This is often used when the MedicationRequest is reported by another person.",
    )
    encounter_field: Reference = Field(
        default=None,
        alias="encounter",
        description="The Encounter during which this [x] was created or to which the creation of this record is tightly associated.",
    )
    supportingInformation_field: List[Reference] = Field(
        default=None,
        alias="supportingInformation",
        description="Information to support fulfilling (i.e. dispensing or administering) of the medication, for example, patient height and weight, a MedicationStatement for the patient).",
    )
    authoredOn_field: dateTimeModel = Field(
        default=None,
        alias="authoredOn",
        description="The date (and perhaps time) when the prescription was initially written or authored on.",
    )
    requester_field: Reference = Field(
        default=None,
        alias="requester",
        description="The individual, organization, or device that initiated the request and has responsibility for its activation.",
    )
    reported_field: booleanModel = Field(
        default=None,
        alias="reported",
        description="Indicates if this record was captured as a secondary 'reported' record rather than as an original primary source-of-truth record.  It may also indicate the source of the report.",
    )
    performerType_field: CodeableConcept = Field(
        default=None,
        alias="performerType",
        description="Indicates the type of performer of the administration of the medication.",
    )
    performer_field: List[Reference] = Field(
        default=None,
        alias="performer",
        description="The specified desired performer of the medication treatment (e.g. the performer of the medication administration).  For devices, this is the device that is intended to perform the administration of the medication.  An IV Pump would be an example of a device that is performing the administration.  Both the IV Pump and the practitioner that set the rate or bolus on the pump can be listed as performers.",
    )
    device_field: List[CodeableReference] = Field(
        default=None,
        alias="device",
        description="The intended type of device that is to be used for the administration of the medication (for example, PCA Pump).",
    )
    recorder_field: Reference = Field(
        default=None,
        alias="recorder",
        description="The person who entered the order on behalf of another individual for example in the case of a verbal or a telephone order.",
    )
    reason_field: List[CodeableReference] = Field(
        default=None,
        alias="reason",
        description="The reason or the indication for ordering or not ordering the medication.",
    )
    courseOfTherapyType_field: CodeableConcept = Field(
        default=None,
        alias="courseOfTherapyType",
        description="The description of the overall pattern of the administration of the medication to the patient.",
    )
    insurance_field: List[Reference] = Field(
        default=None,
        alias="insurance",
        description="Insurance plans, coverage extensions, pre-authorizations and/or pre-determinations that may be required for delivering the requested service.",
    )
    # note_field: List[AnnotationModel] = Field(default=None, alias="note", description="Extra information about the prescription that could not be conveyed by the other attributes.")
    # renderedDosageInstruction_field: markdownModel = Field(default=None, alias="renderedDosageInstruction", description="The full representation of the dose of the medication included in all dosage instructions.  To be used when multiple dosage instructions are included to represent complex dosing such as increasing or tapering doses.")
    effectiveDosePeriod_field: Period = Field(
        default=None,
        alias="effectiveDosePeriod",
        description="The period over which the medication is to be taken.  Where there are multiple dosageInstruction lines (for example, tapering doses), this is the earliest date and the latest end date of the dosageInstructions.",
    )
    dosageInstruction_field: List[Dosage] = Field(
        default=None,
        alias="dosageInstruction",
        description="Specific instructions for how the medication is to be used by the patient.",
    )
    # dispenseRequest_field: MedicationRequest_DispenseRequestModel = Field(default=None, alias="dispenseRequest", description="Indicates the specific details for the dispense or medication supply part of a medication request (also known as a Medication Prescription or Medication Order).  Note that this information is not always sent with the order.  There may be in some settings (e.g. hospitals) institutional or system support for completing the dispense details in the pharmacy department.")
    # substitution_field: MedicationRequest_SubstitutionModel = Field(default=None, alias="substitution", description="Indicates whether or not substitution can or should be part of the dispense. In some cases, substitution must happen, in other cases substitution must not happen. This block explains the prescriber's intent. If nothing is specified substitution may be done.")
    eventHistory_field: List[Reference] = Field(
        default=None,
        alias="eventHistory",
        description="Links to Provenance records for past versions of this resource or fulfilling request or event resources that identify key state transitions or updates that are likely to be relevant to a user looking at the current version of the resource.",
    )
