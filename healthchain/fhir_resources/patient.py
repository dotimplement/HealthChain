from pydantic import Field, BaseModel
from typing import List, Literal

from healthchain.fhir_resources.primitives import (
    idModel,
    uriModel,
    codeModel,
    booleanModel,
    stringModel,
    positiveIntModel,
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


class Address(BaseModel):
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
    use_field: codeModel = Field(
        default=None, alias="use", description="The purpose of this address."
    )
    type_field: codeModel = Field(
        default=None,
        alias="type",
        description="Distinguishes between physical addresses (those you can visit) and mailing addresses (e.g. PO Boxes and care-of addresses). Most addresses are both.",
    )
    text_field: stringModel = Field(
        default=None,
        alias="text",
        description="Specifies the entire address as it should be displayed e.g. on a postal label. This may be provided instead of or as well as the specific parts.",
    )
    line_field: List[stringModel] = Field(
        default=None,
        alias="line",
        description="This component contains the house number, apartment number, street name, street direction,  P.O. Box number, delivery hints, and similar address information.",
    )
    city_field: stringModel = Field(
        default=None,
        alias="city",
        description="The name of the city, town, suburb, village or other community or delivery center.",
    )
    district_field: stringModel = Field(
        default=None,
        alias="district",
        description="The name of the administrative area (county).",
    )
    state_field: stringModel = Field(
        default=None,
        alias="state",
        description="Sub-unit of a country with limited sovereignty in a federally organized country. A code may be used if codes are in common use (e.g. US 2 letter state codes).",
    )
    postalCode_field: stringModel = Field(
        default=None,
        alias="postalCode",
        description="A postal code designating a region defined by the postal service.",
    )
    country_field: stringModel = Field(
        default=None,
        alias="country",
        description="Country - a nation as commonly understood or generally accepted.",
    )
    period_field: Period = Field(
        default=None,
        alias="period",
        description="Time period when address was/is in use.",
    )


class ContactPoint(BaseModel):
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
    system_field: codeModel = Field(
        default=None,
        alias="system",
        description="Telecommunications form for contact point - what communications system is required to make use of the contact.",
    )
    value_field: stringModel = Field(
        default=None,
        alias="value",
        description="The actual contact point details, in a form that is meaningful to the designated communication system (i.e. phone number or email address).",
    )
    use_field: codeModel = Field(
        default=None,
        alias="use",
        description="Identifies the purpose for the contact point.",
    )
    rank_field: positiveIntModel = Field(
        default=None,
        alias="rank",
        description="Specifies a preferred order in which to use a set of contacts. ContactPoints with lower rank values are more preferred than those with higher rank values.",
    )
    period_field: Period = Field(
        default=None,
        alias="period",
        description="Time period when the contact point was/is in use.",
    )


class HumanName(BaseModel):
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
    use_field: codeModel = Field(
        default=None, alias="use", description="Identifies the purpose for this name."
    )
    text_field: stringModel = Field(
        default=None,
        alias="text",
        description="Specifies the entire name as it should be displayed e.g. on an application UI. This may be provided instead of or as well as the specific parts.",
    )
    family_field: stringModel = Field(
        default=None,
        alias="family",
        description="The part of a name that links to the genealogy. In some cultures (e.g. Eritrea) the family name of a son is the first name of his father.",
    )
    given_field: List[stringModel] = Field(
        default=None, alias="given", description="Given name."
    )
    prefix_field: List[stringModel] = Field(
        default=None,
        alias="prefix",
        description="Part of the name that is acquired as a title due to academic, legal, employment or nobility status, etc. and that appears at the start of the name.",
    )
    suffix_field: List[stringModel] = Field(
        default=None,
        alias="suffix",
        description="Part of the name that is acquired as a title due to academic, legal, employment or nobility status, etc. and that appears at the end of the name.",
    )
    period_field: Period = Field(
        default=None,
        alias="period",
        description="Indicates the period of time when this name was valid for the named person.",
    )


class PatientLink(BaseModel):
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
    other_field: Reference = Field(
        default=None,
        alias="other",
        description="Link to a Patient or RelatedPerson resource that concerns the same actual individual.",
    )
    type_field: codeModel = Field(
        default=None,
        alias="type",
        description="The type of link between this patient resource and another patient resource.",
    )


class PatientContact(BaseModel):
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
    relationship_field: List[CodeableConcept] = Field(
        default=None,
        alias="relationship",
        description="The nature of the relationship between the patient and the contact person.",
    )
    name_field: HumanName = Field(
        default=None,
        alias="name",
        description="A name associated with the contact person.",
    )
    telecom_field: List[ContactPoint] = Field(
        default=None,
        alias="telecom",
        description="A contact detail for the person, e.g. a telephone number or an email address.",
    )
    address_field: Address = Field(
        default=None, alias="address", description="Address for the contact person."
    )
    gender_field: codeModel = Field(
        default=None,
        alias="gender",
        description="Administrative Gender - the gender that the contact person is considered to have for administration and record keeping purposes.",
    )
    organization_field: Reference = Field(
        default=None,
        alias="organization",
        description="Organization on behalf of which the contact is acting or for which the contact is working.",
    )
    period_field: Period = Field(
        default=None,
        alias="period",
        description="The period during which this contact person or organization is valid to be contacted relating to this patient.",
    )


class PatientCommunication(BaseModel):
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
        description="Indicates whether or not the patient prefers this language (over other languages he masters up a certain level).",
    )


class Patient(BaseModel):
    resourceType: Literal["Patient"] = "Patient"
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
    # NOTE: The text field has been switched to stringModel rather than NarrativeField for simplicity.
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
        description="An identifier for this patient.",
    )
    active_field: booleanModel = Field(
        default=None,
        alias="active",
        description="Whether this patient record is in active use. ",
    )
    name_field: List[HumanName] = Field(
        default=None,
        alias="name",
        description="A name associated with the individual.",
    )
    telecom_field: List[ContactPoint] = Field(
        default=None,
        alias="telecom",
        description="A contact detail (e.g. a telephone number or an email address) by which the individual may be contacted.",
    )
    gender_field: codeModel = Field(
        default=None,
        alias="gender",
        description="Administrative Gender - the gender that the patient is considered to have for administration and record keeping purposes.",
    )
    birthDate_field: dateModel = Field(
        default=None,
        alias="birthDate",
        description="The date of birth for the individual.",
    )
    address_field: List[Address] = Field(
        default=None,
        alias="address",
        description="An address for the individual.",
    )
    maritalStatus_field: CodeableConcept = Field(
        default=None,
        alias="maritalStatus",
        description="This field contains a patient's most recent marital (civil) status.",
    )
    # photo_field: List[AttachmentModel] = Field(default=None, alias="photo", description="Image of the patient.")
    contact_field: List[PatientContact] = Field(
        default=None,
        alias="contact",
        description="A contact party (e.g. guardian, partner, friend) for the patient.",
    )
    communication_field: List[PatientCommunication] = Field(
        default=None,
        alias="communication",
        description="A language which may be used to communicate with the patient about his or her health.",
    )
    generalPractitioner_field: List[Reference] = Field(
        default=None,
        alias="generalPractitioner",
        description="Patient's nominated care provider.",
    )
    managingOrganization_field: Reference = Field(
        default=None,
        alias="managingOrganization",
        description="Organization that is the custodian of the patient record.",
    )
    link_field: List[PatientLink] = Field(
        default=None,
        alias="link",
        description="Link to a Patient or RelatedPerson resource that concerns the same actual individual.",
    )
