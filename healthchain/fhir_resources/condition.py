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
    Age,
    Range,
    Meta,
    Annotation,
)


class ConditionParticipant(BaseModel):
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
        description="Distinguishes the type of involvement of the actor in the activities related to the condition.",
    )
    actor_field: Reference = Field(
        default=None,
        alias="actor",
        description="Indicates who or what participated in the activities related to the condition.",
    )


class ConditionStage(BaseModel):
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
    summary_field: CodeableConcept = Field(
        default=None,
        alias="summary",
        description="A simple summary of the stage such as Stage 3 or Early Onset. The determination of the stage is disease-specific, such as cancer, retinopathy of prematurity, kidney diseases, Alzheimer's, or Parkinson disease.",
    )
    assessment_field: List[Reference] = Field(
        default=None,
        alias="assessment",
        description="Reference to a formal record of the evidence on which the staging assessment is based.",
    )
    type_field: CodeableConcept = Field(
        default=None,
        alias="type",
        description="The kind of staging, such as pathological or clinical staging.",
    )


class Condition(BaseModel):
    resourceType: Literal["Condition"] = "Condition"
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
        description="Business identifiers assigned to this condition by the performer or other systems which remain constant as the resource is updated and propagates from server to server.",
    )
    clinicalStatus_field: CodeableConcept = Field(
        default=None,
        alias="clinicalStatus",
        description="The clinical status of the condition.",
    )
    verificationStatus_field: CodeableConcept = Field(
        default=None,
        alias="verificationStatus",
        description="The verification status to support the clinical status of the condition.  The verification status pertains to the condition, itself, not to any specific condition attribute.",
    )
    category_field: List[CodeableConcept] = Field(
        default=None,
        alias="category",
        description="A category assigned to the condition.",
    )
    severity_field: CodeableConcept = Field(
        default=None,
        alias="severity",
        description="A subjective assessment of the severity of the condition as evaluated by the clinician.",
    )
    code_field: CodeableConcept = Field(
        default=None,
        alias="code",
        description="Identification of the condition, problem or diagnosis.",
    )
    bodySite_field: List[CodeableConcept] = Field(
        default=None,
        alias="bodySite",
        description="The anatomical location where this condition manifests itself.",
    )
    subject_field: Reference = Field(
        default=None,
        alias="subject",
        description="Indicates the patient or group who the condition record is associated with.",
    )
    encounter_field: Reference = Field(
        default=None,
        alias="encounter",
        description="The Encounter during which this Condition was created or to which the creation of this record is tightly associated.",
    )
    onsetDateTime_field: dateTimeModel = Field(
        default=None,
        alias="onsetDateTime",
        description="Estimated or actual date or date-time  the condition began, in the opinion of the clinician.",
    )
    onsetAge_field: Age = Field(
        default=None,
        alias="onsetAge",
        description="Estimated or actual date or date-time  the condition began, in the opinion of the clinician.",
    )
    onsetPeriod_field: Period = Field(
        default=None,
        alias="onsetPeriod",
        description="Estimated or actual date or date-time  the condition began, in the opinion of the clinician.",
    )
    onsetRange_field: Range = Field(
        default=None,
        alias="onsetRange",
        description="Estimated or actual date or date-time  the condition began, in the opinion of the clinician.",
    )
    abatementDateTime_field: dateTimeModel = Field(
        default=None,
        alias="abatementDateTime",
        description="The date or estimated date that the condition resolved or went into remission. This is called abatement because of the many overloaded connotations associated with remission or resolution - Some conditions, such as chronic conditions, are never really resolved, but they can abate.",
    )
    abatementAge_field: Age = Field(
        default=None,
        alias="abatementAge",
        description="The date or estimated date that the condition resolved or went into remission. This is called abatement because of the many overloaded connotations associated with remission or resolution - Some conditions, such as chronic conditions, are never really resolved, but they can abate.",
    )
    abatementPeriod_field: Period = Field(
        default=None,
        alias="abatementPeriod",
        description="The date or estimated date that the condition resolved or went into remission. This is called abatement because of the many overloaded connotations associated with remission or resolution - Some conditions, such as chronic conditions, are never really resolved, but they can abate.",
    )
    abatementRange_field: Range = Field(
        default=None,
        alias="abatementRange",
        description="The date or estimated date that the condition resolved or went into remission. This is called abatement because of the many overloaded connotations associated with remission or resolution - Some conditions, such as chronic conditions, are never really resolved, but they can abate.",
    )
    recordedDate_field: dateTimeModel = Field(
        default=None,
        alias="recordedDate",
        description="The recordedDate represents when this particular Condition record was created in the system, which is often a system-generated date.",
    )
    participant_field: List[ConditionParticipant] = Field(
        default=None,
        alias="participant",
        description="Indicates who or what participated in the activities related to the condition and how they were involved.",
    )
    stage_field: List[ConditionStage] = Field(
        default=None,
        alias="stage",
        description="A simple summary of the stage such as Stage 3 or Early Onset. The determination of the stage is disease-specific, such as cancer, retinopathy of prematurity, kidney diseases, Alzheimer's, or Parkinson disease.",
    )
    evidence_field: List[CodeableReference] = Field(
        default=None,
        alias="evidence",
        description="Supporting evidence / manifestations that are the basis of the Condition's verification status, such as evidence that confirmed or refuted the condition.",
    )
    note_field: List[Annotation] = Field(
        default=None,
        alias="note",
        description="Additional information about the Condition. This is a general notes/comments entry  for description of the Condition, its diagnosis and prognosis.",
    )
