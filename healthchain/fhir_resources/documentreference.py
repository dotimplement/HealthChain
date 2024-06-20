from pydantic import BaseModel, Field
from typing import List, Literal

from healthchain.fhir_resources.primitives import (
    idModel,
    uriModel,
    codeModel,
    dateTimeModel,
    instantModel,
    markdownModel,
    stringModel,
)
from healthchain.fhir_resources.generalpurpose import (
    Extension,
    CodeableConcept,
    Reference,
    Period,
    Narrative,
    CodeableReference,
    Coding,
    Attachment,
    Identifier,
    Meta,
)


class DocumentReferenceAttester(BaseModel):
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
    mode_field: CodeableConcept = Field(
        default=None,
        alias="mode",
        description="The type of attestation the authenticator offers.",
    )
    time_field: dateTimeModel = Field(
        default=None,
        alias="time",
        description="When the document was attested by the party.",
    )
    party_field: Reference = Field(
        default=None,
        alias="party",
        description="Who attested the document in the specified way.",
    )


class DocumentReferenceRelatesTo(BaseModel):
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
    code_field: CodeableConcept = Field(
        default=None,
        alias="code",
        description="The type of relationship that this document has with anther document.",
    )
    target_field: Reference = Field(
        default=None,
        alias="target",
        description="The target document of this relationship.",
    )


class DocumentReferenceProfile(BaseModel):
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
    valueCoding_field: Coding = Field(
        default=None, alias="valueCoding", description="Code|uri|canonical."
    )


class DocumentReferenceContent(BaseModel):
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
    attachment_field: Attachment = Field(
        default=None,
        alias="attachment",
        description="The document or URL of the document along with critical metadata to prove content has integrity.",
    )
    profile_field: List[DocumentReferenceProfile] = Field(
        default=None,
        alias="profile",
        description="An identifier of the document constraints, encoding, structure, and template that the document conforms to beyond the base format indicated in the mimeType.",
    )


class DocumentReference(BaseModel):
    resourceType: Literal["DocumentReference"] = "DocumentReference"
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
        description="Other business identifiers associated with the document, including version independent identifiers.",
    )
    version_field: stringModel = Field(
        default=None,
        alias="version",
        description="An explicitly assigned identifer of a variation of the content in the DocumentReference.",
    )
    basedOn_field: List[Reference] = Field(
        default=None,
        alias="basedOn",
        description="A procedure that is fulfilled in whole or in part by the creation of this media.",
    )
    status_field: codeModel = Field(
        default=None,
        alias="status",
        description="The status of this document reference.",
    )
    docStatus_field: codeModel = Field(
        default=None,
        alias="docStatus",
        description="The status of the underlying document.",
    )
    modality_field: List[CodeableConcept] = Field(
        default=None,
        alias="modality",
        description="Imaging modality used. This may include both acquisition and non-acquisition modalities.",
    )
    type_field: CodeableConcept = Field(
        default=None,
        alias="type",
        description="Specifies the particular kind of document referenced  (e.g. History and Physical, Discharge Summary, Progress Note). This usually equates to the purpose of making the document referenced.",
    )
    category_field: List[CodeableConcept] = Field(
        default=None,
        alias="category",
        description="A categorization for the type of document referenced - helps for indexing and searching. This may be implied by or derived from the code specified in the DocumentReference.type.",
    )
    subject_field: Reference = Field(
        default=None,
        alias="subject",
        description="Who or what the document is about. The document can be about a person, (patient or healthcare practitioner), a device (e.g. a machine) or even a group of subjects (such as a document about a herd of farm animals, or a set of patients that share a common exposure).",
    )
    context_field: List[Reference] = Field(
        default=None,
        alias="context",
        description="Describes the clinical encounter or type of care that the document content is associated with.",
    )
    event_field: List[CodeableReference] = Field(
        default=None,
        alias="event",
        description="This list of codes represents the main clinical acts, such as a colonoscopy or an appendectomy, being documented. In some cases, the event is inherent in the type Code, such as a History and Physical Report in which the procedure being documented is necessarily a History and Physical act.",
    )
    bodySite_field: List[CodeableReference] = Field(
        default=None,
        alias="bodySite",
        description="The anatomic structures included in the document.",
    )
    facilityType_field: CodeableConcept = Field(
        default=None,
        alias="facilityType",
        description="The kind of facility where the patient was seen.",
    )
    practiceSetting_field: CodeableConcept = Field(
        default=None,
        alias="practiceSetting",
        description="This property may convey specifics about the practice setting where the content was created, often reflecting the clinical specialty.",
    )
    period_field: Period = Field(
        default=None,
        alias="period",
        description="The time period over which the service that is described by the document was provided.",
    )
    date_field: instantModel = Field(
        default=None,
        alias="date",
        description="When the document reference was created.",
    )
    author_field: List[Reference] = Field(
        default=None,
        alias="author",
        description="Identifies who is responsible for adding the information to the document.",
    )
    attester_field: List[DocumentReferenceAttester] = Field(
        default=None,
        alias="attester",
        description="A participant who has authenticated the accuracy of the document.",
    )
    custodian_field: Reference = Field(
        default=None,
        alias="custodian",
        description="Identifies the organization or group who is responsible for ongoing maintenance of and access to the document.",
    )
    relatesTo_field: List[DocumentReferenceRelatesTo] = Field(
        default=None,
        alias="relatesTo",
        description="Relationships that this document has with other document references that already exist.",
    )
    description_field: markdownModel = Field(
        default=None,
        alias="description",
        description="Human-readable description of the source document.",
    )
    securityLabel_field: List[CodeableConcept] = Field(
        default=None,
        alias="securityLabel",
        description="A set of Security-Tag codes specifying the level of privacy/security of the Document found at DocumentReference.content.attachment.url. Note that DocumentReference.meta.security contains the security labels of the data elements in DocumentReference, while DocumentReference.securityLabel contains the security labels for the document the reference refers to. The distinction recognizes that the document may contain sensitive information, while the DocumentReference is metadata about the document and thus might not be as sensitive as the document. For example: a psychotherapy episode may contain highly sensitive information, while the metadata may simply indicate that some episode happened.",
    )
    content_field: List[DocumentReferenceContent] = Field(
        default=None,
        alias="content",
        description="The document and format referenced.  If there are multiple content element repetitions, these must all represent the same document in different format, or attachment metadata.",
    )
