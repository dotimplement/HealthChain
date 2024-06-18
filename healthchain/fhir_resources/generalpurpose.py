from __future__ import annotations

from typing import List
from pydantic import BaseModel, Field

from healthchain.fhir_resources.primitives import (
    stringModel,
    uriModel,
    dateTimeModel,
    codeModel,
    booleanModel,
    markdownModel,
    decimalModel,
    comparatorModel,
    positiveIntModel,
    canonicalModel,
    unsignedIntModel,
    idModel,
    instantModel,
    timeModel,
    integer64Model,
    urlModel,
)


class Extension(BaseModel):
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
    url_field: uriModel = Field(
        default=None,
        alias="url",
        description="Source of the definition for the extension code - a logical name or a URL.",
    )


class Period(BaseModel):
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
    start_field: dateTimeModel = Field(
        default=None,
        alias="start",
        description="The start of the period. The boundary is inclusive.",
    )
    end_field: dateTimeModel = Field(
        default=None,
        alias="end",
        description="The end of the period. If the end of the period is missing, it means no end was known or planned at the time the instance was created. The start may be in the past, and the end date in the future, which means that period is expected/planned to end at that time.",
    )


class Identifier(BaseModel):
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
    # Identifier_use_field: useModel = Field(..., alias="use", description="The purpose of this identifier.")
    type_field: CodeableConcept = Field(
        default=None,
        alias="type",
        description="A coded type for the identifier that can be used to determine which identifier to use for a specific purpose.",
    )
    system_field: uriModel = Field(
        default=None,
        alias="system",
        description="Establishes the namespace for the value - that is, an absolute URL that describes a set values that are unique.",
    )
    value_field: stringModel = Field(
        default=None,
        alias="value",
        description="The portion of the identifier typically relevant to the user and which is unique within the context of the system.",
    )
    period_field: Period = Field(
        default=None,
        alias="period",
        description="Time period during which identifier is/was valid for use.",
    )
    assigner_field: Reference = Field(
        default=None,
        alias="assigner",
        description="Organization that issued/manages the identifier.",
    )


class Coding(BaseModel):
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
    system_field: uriModel = Field(
        default=None,
        alias="system",
        description="The identification of the code system that defines the meaning of the symbol in the code.",
    )
    version_field: stringModel = Field(
        default=None,
        alias="version",
        description="The version of the code system which was used when choosing this code. Note that a well-maintained code system does not need the version reported, because the meaning of codes is consistent across versions. However this cannot consistently be assured, and when the meaning is not guaranteed to be consistent, the version SHOULD be exchanged.",
    )
    code_field: codeModel = Field(
        default=None,
        alias="code",
        description="A symbol in syntax defined by the system. The symbol may be a predefined code or an expression in a syntax defined by the coding system (e.g. post-coordination).",
    )
    display_field: stringModel = Field(
        default=None,
        alias="display",
        description="A representation of the meaning of the code in the system, following the rules of the system.",
    )
    userSelected_field: booleanModel = Field(
        default=None,
        alias="userSelected",
        description="Indicates that this coding was chosen by a user directly - e.g. off a pick list of available items (codes or displays).",
    )


class CodeableConcept(BaseModel):
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
    coding_field: List[Coding] = Field(
        default=None,
        alias="coding",
        description="A reference to a code defined by a terminology system.",
    )
    text_field: stringModel = Field(
        default=None,
        alias="text",
        description="A human language representation of the concept as seen/selected/uttered by the user who entered the data and/or which represents the intended meaning of the user.",
    )


class Reference(BaseModel):
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
    reference_field: stringModel = Field(
        default=None,
        alias="reference",
        description="A reference to a location at which the other resource is found. The reference may be a relative reference, in which case it is relative to the service base URL, or an absolute URL that resolves to the location where the resource is found. The reference may be version specific or not. If the reference is not to a FHIR RESTful server, then it should be assumed to be version specific. Internal fragment references (start with '#') refer to contained resources.",
    )
    type_field: uriModel = Field(
        default=None,
        alias="type",
        description="The expected type of the target of the reference. If both Reference.type and Reference.reference are populated and Reference.reference is a FHIR URL, both SHALL be consistent.",
    )
    identifier_field: Identifier = Field(
        default=None,
        alias="identifier",
        description="An identifier for the target resource. This is used when there is no way to reference the other resource directly, either because the entity it represents is not available through a FHIR server, or because there is no way for the author of the resource to convert a known identifier to an actual location. There is no requirement that a Reference.identifier point to something that is actually exposed as a FHIR instance, but it SHALL point to a business concept that would be expected to be exposed as a FHIR instance, and that instance would need to be of a FHIR resource type allowed by the reference.",
    )
    display_field: stringModel = Field(
        default=None,
        alias="display",
        description="Plain text narrative that identifies the resource in addition to the resource reference.",
    )


class CodeableReference(BaseModel):
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
    concept_field: CodeableConcept = Field(
        default=None,
        alias="concept",
        description="A reference to a concept - e.g. the information is identified by its general class to the degree of precision found in the terminology.",
    )
    reference_field: Reference = Field(
        default=None,
        alias="reference",
        description="A reference to a resource the provides exact details about the information being referenced.",
    )


class Narrative(BaseModel):
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
    # Narrative_status_field: statusModel = Field(..., alias="status", description="The status of the narrative - whether it's entirely generated (from just the defined data or the extensions too), or whether a human authored it and it may contain additional data.")
    div_field: stringModel = Field(
        default=None,
        alias="div",
        description="The actual narrative content, a stripped down version of XHTML.",
    )


class Age(BaseModel):
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
    value_field: decimalModel = Field(
        default=None,
        alias="value",
        description="The value of the measured amount. The value includes an implicit precision in the presentation of the value.",
    )
    age_comparator_field: comparatorModel = Field(
        ...,
        alias="comparator",
        description="How the value should be understood and represented - whether the actual value is greater or less than the stated value due to measurement issues; e.g. if the comparator is < , then the real value is < stated value.",
    )
    unit_field: stringModel = Field(
        default=None, alias="unit", description="A human-readable form of the unit."
    )
    system_field: uriModel = Field(
        default=None,
        alias="system",
        description="The identification of the system that provides the coded form of the unit.",
    )
    code_field: codeModel = Field(
        default=None,
        alias="code",
        description="A computer processable form of the unit in some unit representation system.",
    )


class Quantity(BaseModel):
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
    value_field: decimalModel = Field(
        default=None,
        alias="value",
        description="The value of the measured amount. The value includes an implicit precision in the presentation of the value.",
    )
    # Quantity_comparator_field: comparatorModel = Field(..., alias="comparator", description="How the value should be understood and represented - whether the actual value is greater or less than the stated value due to measurement issues; e.g. if the comparator is < , then the real value is < stated value.")
    unit_field: stringModel = Field(
        default=None, alias="unit", description="A human-readable form of the unit."
    )
    system_field: uriModel = Field(
        default=None,
        alias="system",
        description="The identification of the system that provides the coded form of the unit.",
    )
    code_field: codeModel = Field(
        default=None,
        alias="code",
        description="A computer processable form of the unit in some unit representation system.",
    )


class Range(BaseModel):
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
    low_field: Quantity = Field(
        default=None,
        alias="low",
        description="The low limit. The boundary is inclusive.",
    )
    high_field: Quantity = Field(
        default=None,
        alias="high",
        description="The high limit. The boundary is inclusive.",
    )


class Ratio(BaseModel):
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
    numerator_field: Quantity = Field(
        default=None, alias="numerator", description="The value of the numerator."
    )
    denominator_field: Quantity = Field(
        default=None, alias="denominator", description="The value of the denominator."
    )


class Timing(BaseModel):
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
    event_field: List[dateTimeModel] = Field(
        default=None,
        alias="event",
        description="Identifies specific times when the event occurs.",
    )
    repeat_field: TimingRepeat = Field(
        default=None,
        alias="repeat",
        description="A set of rules that describe when the event is scheduled.",
    )
    code_field: CodeableConcept = Field(
        default=None,
        alias="code",
        description="A code for the timing schedule (or just text in code.text). Some codes such as BID are ubiquitous, but many institutions define their own additional codes. If a code is provided, the code is understood to be a complete statement of whatever is specified in the structured timing data, and either the code or the data may be used to interpret the Timing, with the exception that .repeat.bounds still applies over the code (and is not contained in the code).",
    )


class TimingRepeat(BaseModel):
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
    boundsDuration_field: Duration = Field(
        default=None,
        alias="boundsDuration",
        description="Either a duration for the length of the timing schedule, a range of possible length, or outer bounds for start and/or end limits of the timing schedule.",
    )
    boundsRange_field: Range = Field(
        default=None,
        alias="boundsRange",
        description="Either a duration for the length of the timing schedule, a range of possible length, or outer bounds for start and/or end limits of the timing schedule.",
    )
    boundsPeriod_field: Period = Field(
        default=None,
        alias="boundsPeriod",
        description="Either a duration for the length of the timing schedule, a range of possible length, or outer bounds for start and/or end limits of the timing schedule.",
    )
    count_field: positiveIntModel = Field(
        default=None,
        alias="count",
        description="A total count of the desired number of repetitions across the duration of the entire timing specification. If countMax is present, this element indicates the lower bound of the allowed range of count values.",
    )
    countMax_field: positiveIntModel = Field(
        default=None,
        alias="countMax",
        description="If present, indicates that the count is a range - so to perform the action between [count] and [countMax] times.",
    )
    duration_field: decimalModel = Field(
        default=None,
        alias="duration",
        description="How long this thing happens for when it happens. If durationMax is present, this element indicates the lower bound of the allowed range of the duration.",
    )
    durationMax_field: decimalModel = Field(
        default=None,
        alias="durationMax",
        description="If present, indicates that the duration is a range - so to perform the action between [duration] and [durationMax] time length.",
    )
    # Timing_Repeat_durationUnit_field: durationUnitModel = Field(..., alias="durationUnit", description="The units of time for the duration, in UCUM units")
    frequency_field: positiveIntModel = Field(
        default=None,
        alias="frequency",
        description="The number of times to repeat the action within the specified period. If frequencyMax is present, this element indicates the lower bound of the allowed range of the frequency.",
    )
    frequencyMax_field: positiveIntModel = Field(
        default=None,
        alias="frequencyMax",
        description="If present, indicates that the frequency is a range - so to repeat between [frequency] and [frequencyMax] times within the period or period range.",
    )
    period_field: decimalModel = Field(
        default=None,
        alias="period",
        description="Indicates the duration of time over which repetitions are to occur; e.g. to express 3 times per day, 3 would be the frequency and 1 day would be the period. If periodMax is present, this element indicates the lower bound of the allowed range of the period length.",
    )
    periodMax_field: decimalModel = Field(
        default=None,
        alias="periodMax",
        description="If present, indicates that the period is a range from [period] to [periodMax], allowing expressing concepts such as do this once every 3-5 days.",
    )
    # Timing_Repeat_periodUnit_field: periodUnitModel = Field(..., alias="periodUnit", description="The units of time for the period in UCUM units")
    dayOfWeek_field: List[codeModel] = Field(
        default=None,
        alias="dayOfWeek",
        description="If one or more days of week is provided, then the action happens only on the specified day(s).",
    )
    timeOfDay_field: List[timeModel] = Field(
        default=None,
        alias="timeOfDay",
        description="Specified time of day for action to take place.",
    )
    offset_field: unsignedIntModel = Field(
        default=None,
        alias="offset",
        description="The number of minutes from the event. If the event code does not indicate whether the minutes is before or after the event, then the offset is assumed to be after the event.",
    )


class Meta(BaseModel):
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
    versionId_field: idModel = Field(
        default=None,
        alias="versionId",
        description="The version specific identifier, as it appears in the version portion of the URL. This value changes when the resource is created, updated, or deleted.",
    )
    lastUpdated_field: instantModel = Field(
        default=None,
        alias="lastUpdated",
        description="When the resource last changed - e.g. when the version changed.",
    )
    source_field: uriModel = Field(
        default=None,
        alias="source",
        description="A uri that identifies the source system of the resource. This provides a minimal amount of [[[Provenance]]] information that can be used to track or differentiate the source of information in the resource. The source may identify another FHIR server, document, message, database, etc.",
    )
    profile_field: List[canonicalModel] = Field(
        default=None,
        alias="profile",
        description="A list of profiles (references to [[[StructureDefinition]]] resources) that this resource claims to conform to. The URL is a reference to [[[StructureDefinition.url]]].",
    )
    security_field: List[Coding] = Field(
        default=None,
        alias="security",
        description="Security labels applied to this resource. These tags connect specific resources to the overall security policy and infrastructure.",
    )
    tag_field: List[Coding] = Field(
        default=None,
        alias="tag",
        description="Tags applied to this resource. Tags are intended to be used to identify and relate resources to process and workflow, and applications are not required to consider the tags when interpreting the meaning of a resource.",
    )


class Duration(BaseModel):
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
    value_field: decimalModel = Field(
        default=None,
        alias="value",
        description="The value of the measured amount. The value includes an implicit precision in the presentation of the value.",
    )
    # Duration_comparator_field: comparatorModel = Field(..., alias="comparator", description="How the value should be understood and represented - whether the actual value is greater or less than the stated value due to measurement issues; e.g. if the comparator is < , then the real value is < stated value.")
    unit_field: stringModel = Field(
        default=None, alias="unit", description="A human-readable form of the unit."
    )
    system_field: uriModel = Field(
        default=None,
        alias="system",
        description="The identification of the system that provides the coded form of the unit.",
    )
    code_field: codeModel = Field(
        default=None,
        alias="code",
        description="A computer processable form of the unit in some unit representation system.",
    )


class Annotation(BaseModel):
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
    authorReference_field: Reference = Field(
        default=None,
        alias="authorReference",
        description="The individual responsible for making the annotation.",
    )
    time_field: dateTimeModel = Field(
        default=None,
        alias="time",
        description="Indicates when this particular annotation was made.",
    )
    text_field: markdownModel = Field(
        default=None,
        alias="text",
        description="The text of the annotation in markdown format.",
    )


class Attachment(BaseModel):
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
    contentType_field: codeModel = Field(
        default=None,
        alias="contentType",
        description="Identifies the type of the data in the attachment and allows a method to be chosen to interpret or render the data. Includes mime type parameters such as charset where appropriate.",
    )
    language_field: codeModel = Field(
        default=None,
        alias="language",
        description="The human language of the content. The value can be any valid value according to BCP 47.",
    )
    data_field: stringModel = Field(
        default=None,
        alias="data",
        description="The actual data of the attachment - a sequence of bytes, base64 encoded.",
    )
    url_field: urlModel = Field(
        default=None,
        alias="url",
        description="A location where the data can be accessed.",
    )
    size_field: integer64Model = Field(
        default=None,
        alias="size",
        description="The number of bytes of data that make up this attachment (before base64 encoding, if that is done).",
    )
    hash_field: stringModel = Field(
        default=None,
        alias="hash",
        description="The calculated hash of the data using SHA-1. Represented using base64.",
    )
    title_field: stringModel = Field(
        default=None,
        alias="title",
        description="A label or set of text to display in place of the data.",
    )
    creation_field: dateTimeModel = Field(
        default=None,
        alias="creation",
        description="The date that the attachment was first created.",
    )
    height_field: positiveIntModel = Field(
        default=None,
        alias="height",
        description="Height of the image in pixels (photo/video).",
    )
    width_field: positiveIntModel = Field(
        default=None,
        alias="width",
        description="Width of the image in pixels (photo/video).",
    )
    frames_field: positiveIntModel = Field(
        default=None,
        alias="frames",
        description="The number of frames in a photo. This is used with a multi-page fax, or an imaging acquisition context that takes multiple slices in a single image, or an animated gif. If there is more than one frame, this SHALL have a value in order to alert interface software that a multi-frame capable rendering widget is required.",
    )
    duration_field: decimalModel = Field(
        default=None,
        alias="duration",
        description="The duration of the recording in seconds - for audio and video.",
    )
    pages_field: positiveIntModel = Field(
        default=None, alias="pages", description="The number of pages when printed."
    )
