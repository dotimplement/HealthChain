from pydantic import Field, BaseModel
from typing import List, Literal

from healthchain.fhir_resources.primitives import (
    idModel,
    uriModel,
    codeModel,
    booleanModel,
    stringModel,
    dateModel,
)
from healthchain.fhir_resources.generalpurpose import (
    Identifier,
    Reference,
    Extension,
    Period,
    CodeableConcept,
    Meta,
    Narrative,
)
from healthchain.fhir_resources.patient import (
    HumanName,
    ContactPoint,
    Address,
)


class PractitionerQualification(BaseModel):
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
    identifier_field: List[Identifier] = Field(
        default=None,
        alias="identifier",
        description="An identifier that applies to this person's qualification.",
    )
    code_field: CodeableConcept = Field(
        default=None,
        alias="code",
        description="Coded representation of the qualification.",
    )
    period_field: Period = Field(
        default=None,
        alias="period",
        description="Period during which the qualification is valid.",
    )
    issuer_field: Reference = Field(
        default=None,
        alias="issuer",
        description="Organization that regulates and issues the qualification.",
    )


class PractitionerCommunication(BaseModel):
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
    language_field: CodeableConcept = Field(
        default=None,
        alias="language",
        description="The ISO-639-1 alpha 2 code in lower case for the language, optionally followed by a hyphen and the ISO-3166-1 alpha 2 code for the region in upper case; e.g. en for English, or en-US for American English versus en-AU for Australian English.",
    )
    preferred_field: booleanModel = Field(
        default=None,
        alias="preferred",
        description="Indicates whether or not the person prefers this language (over other languages he masters up a certain level).",
    )


class Practitioner(BaseModel):
    resourceType: Literal["Practitioner"] = "Practitioner"
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
        description="An identifier that applies to this person in this role.",
    )
    active_field: booleanModel = Field(
        default=None,
        alias="active",
        description="Whether this practitioner's record is in active use.",
    )
    name_field: List[HumanName] = Field(
        default=None,
        alias="name",
        description="The name(s) associated with the practitioner.",
    )
    telecom_field: List[ContactPoint] = Field(
        default=None,
        alias="telecom",
        description="A contact detail for the practitioner, e.g. a telephone number or an email address.",
    )
    gender_field: codeModel = Field(
        default=None,
        alias="gender",
        description="Administrative Gender - the gender that the person is considered to have for administration and record keeping purposes.",
    )
    birthDate_field: dateModel = Field(
        default=None,
        alias="birthDate",
        description="The date of birth for the practitioner.",
    )
    address_field: List[Address] = Field(
        default=None,
        alias="address",
        description="Address(es) of the practitioner that are not role specific (typically home address). ",
    )
    # photo_field: List[AttachmentModel] = Field(default=None, alias="photo", description="Image of the person.")
    qualification_field: List[PractitionerQualification] = Field(
        default=None,
        alias="qualification",
        description="The official qualifications, certifications, accreditations, training, licenses (and other types of educations/skills/capabilities) that authorize or otherwise pertain to the provision of care by the practitioner.",
    )
    communication_field: List[PractitionerCommunication] = Field(
        default=None,
        alias="communication",
        description="A language which may be used to communicate with the practitioner, often for correspondence/administrative purposes.",
    )
