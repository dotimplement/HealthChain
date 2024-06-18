from pydantic import BaseModel, Field
from typing import List, Literal

from healthchain.fhir_resources.primitives import (
    stringModel,
    idModel,
    uriModel,
    codeModel,
    dateTimeModel,
    booleanModel,
)
from healthchain.fhir_resources.generalpurpose import (
    Extension,
    Identifier,
    CodeableConcept,
    Reference,
    Period,
    CodeableReference,
    Narrative,
    Quantity,
    Timing,
    Ratio,
    Meta,
    Annotation,
)


class MedicationAdministrationPerformer(BaseModel):
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
        description="Distinguishes the type of involvement of the performer in the medication administration.",
    )
    actor_field: CodeableReference = Field(
        default=None,
        alias="actor",
        description="Indicates who or what performed the medication administration.",
    )


class MedicationAdministrationDosage(BaseModel):
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
    text_field: stringModel = Field(
        default=None,
        alias="text",
        description="Free text dosage can be used for cases where the dosage administered is too complex to code. When coded dosage is present, the free text dosage may still be present for display to humans.",
    )
    site_field: CodeableConcept = Field(
        default=None,
        alias="site",
        description="A coded specification of the anatomic site where the medication first entered the body.  For example, left arm.",
    )
    route_field: CodeableConcept = Field(
        default=None,
        alias="route",
        description="A code specifying the route or physiological path of administration of a therapeutic agent into or onto the patient.  For example, topical, intravenous, etc.",
    )
    method_field: CodeableConcept = Field(
        default=None,
        alias="method",
        description="A coded value indicating the method by which the medication is intended to be or was introduced into or on the body.  This attribute will most often NOT be populated.  It is most commonly used for injections.  For example, Slow Push, Deep IV.",
    )
    dose_field: Quantity = Field(
        default=None,
        alias="dose",
        description="The amount of the medication given at one administration event.   Use this value when the administration is essentially an instantaneous event such as a swallowing a tablet or giving an injection.",
    )
    rateRatio_field: Ratio = Field(
        default=None,
        alias="rateRatio",
        description="Identifies the speed with which the medication was or will be introduced into the patient.  Typically, the rate for an infusion e.g. 100 ml per 1 hour or 100 ml/hr.  May also be expressed as a rate per unit of time, e.g. 500 ml per 2 hours.  Other examples:  200 mcg/min or 200 mcg/1 minute; 1 liter/8 hours.",
    )
    rateQuantity_field: Quantity = Field(
        default=None,
        alias="rateQuantity",
        description="Identifies the speed with which the medication was or will be introduced into the patient.  Typically, the rate for an infusion e.g. 100 ml per 1 hour or 100 ml/hr.  May also be expressed as a rate per unit of time, e.g. 500 ml per 2 hours.  Other examples:  200 mcg/min or 200 mcg/1 minute; 1 liter/8 hours.",
    )


class MedicationAdministration(BaseModel):
    resourceType: Literal["MedicationAdministration"] = "MedicationAdministration"
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
        description="Identifiers associated with this Medication Administration that are defined by business processes and/or used to refer to it when a direct URL reference to the resource itself is not appropriate. They are business identifiers assigned to this resource by the performer or other systems and remain constant as the resource is updated and propagates from server to server.",
    )
    basedOn_field: List[Reference] = Field(
        default=None,
        alias="basedOn",
        description="A plan that is fulfilled in whole or in part by this MedicationAdministration.",
    )
    partOf_field: List[Reference] = Field(
        default=None,
        alias="partOf",
        description="A larger event of which this particular event is a component or step.",
    )
    status_field: codeModel = Field(
        default=None,
        alias="status",
        description="Will generally be set to show that the administration has been completed.  For some long running administrations such as infusions, it is possible for an administration to be started but not completed or it may be paused while some other process is under way.",
    )
    statusReason_field: List[CodeableConcept] = Field(
        default=None,
        alias="statusReason",
        description="A code indicating why the administration was not performed.",
    )
    category_field: List[CodeableConcept] = Field(
        default=None,
        alias="category",
        description="The type of medication administration (for example, drug classification like ATC, where meds would be administered, legal category of the medication).",
    )
    medication_field: CodeableReference = Field(
        default=None,
        alias="medication",
        description="Identifies the medication that was administered. This is either a link to a resource representing the details of the medication or a simple attribute carrying a code that identifies the medication from a known list of medications.",
    )
    subject_field: Reference = Field(
        default=None,
        alias="subject",
        description="The person or animal or group receiving the medication.",
    )
    encounter_field: Reference = Field(
        default=None,
        alias="encounter",
        description="The visit, admission, or other contact between patient and health care provider during which the medication administration was performed.",
    )
    supportingInformation_field: List[Reference] = Field(
        default=None,
        alias="supportingInformation",
        description="Additional information (for example, patient height and weight) that supports the administration of the medication.  This attribute can be used to provide documentation of specific characteristics of the patient present at the time of administration.  For example, if the dose says give x if the heartrate exceeds y, then the heart rate can be included using this attribute.",
    )
    occurencePeriod_field: Period = Field(
        default=None,
        alias="occurencePeriod",
        description="A specific date/time or interval of time during which the administration took place (or did not take place). For many administrations, such as swallowing a tablet the use of dateTime is more appropriate.",
    )
    occurenceTiming_field: Timing = Field(
        default=None,
        alias="occurenceTiming",
        description="A specific date/time or interval of time during which the administration took place (or did not take place). For many administrations, such as swallowing a tablet the use of dateTime is more appropriate.",
    )
    recorded_field: dateTimeModel = Field(
        default=None,
        alias="recorded",
        description="The date the occurrence of the  MedicationAdministration was first captured in the record - potentially significantly after the occurrence of the event.",
    )
    isSubPotent_field: booleanModel = Field(
        default=None,
        alias="isSubPotent",
        description="An indication that the full dose was not administered.",
    )
    subPotentReason_field: List[CodeableConcept] = Field(
        default=None,
        alias="subPotentReason",
        description="The reason or reasons why the full dose was not administered.",
    )
    performer_field: List[MedicationAdministrationPerformer] = Field(
        default=None,
        alias="performer",
        description="The performer of the medication treatment.  For devices this is the device that performed the administration of the medication.  An IV Pump would be an example of a device that is performing the administration. Both the IV Pump and the practitioner that set the rate or bolus on the pump can be listed as performers.",
    )
    reason_field: List[CodeableReference] = Field(
        default=None,
        alias="reason",
        description="A code, Condition or observation that supports why the medication was administered.",
    )
    request_field: Reference = Field(
        default=None,
        alias="request",
        description="The original request, instruction or authority to perform the administration.",
    )
    device_field: List[CodeableReference] = Field(
        default=None,
        alias="device",
        description="The device that is to be used for the administration of the medication (for example, PCA Pump).",
    )
    note_field: List[Annotation] = Field(
        default=None,
        alias="note",
        description="Extra information about the medication administration that is not conveyed by the other attributes.",
    )
    dosage_field: MedicationAdministrationDosage = Field(
        default=None,
        alias="dosage",
        description="Describes the medication dosage information details e.g. dose, rate, site, route, etc.",
    )
    eventHistory_field: List[Reference] = Field(
        default=None,
        alias="eventHistory",
        description="A summary of the events of interest that have occurred, such as when the administration was verified.",
    )
