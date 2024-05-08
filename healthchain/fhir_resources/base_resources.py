
from __future__ import annotations

from pydantic import BaseModel, Field, conint
from typing_extensions import Annotated
from typing import List

class booleanModel(BaseModel):
    boolean: str = Field(pattern=r'^true|false$')

    class Config:
        schema_extra = {
            "description": "Value of true or false"
        }


class canonicalModel(BaseModel):
    canonical: str = Field(pattern=r'^\S*$')

    class Config:
        schema_extra = {
            "description": "A URI that is a reference to a canonical URL on a FHIR resource"
        }


class codeModel(BaseModel):
    code: str = Field(pattern=r'^[^\s]+( [^\s]+)*$')

    class Config:
        schema_extra = {
            "description": "A string which has at least one character and no leading or trailing whitespace and where there is no whitespace other than single spaces in the contents"
        }


class dateModel(BaseModel):
    date: str = Field(pattern=r'^([0-9]([0-9]([0-9][1-9]|[1-9]0)|[1-9]00)|[1-9]000)(-(0[1-9]|1[0-2])(-(0[1-9]|[1-2][0-9]|3[0-1]))?)?$')

    class Config:
        schema_extra = {
            "description": "A date or partial date (e.g. just year or year + month). There is no UTC offset. The format is a union of the schema types gYear, gYearMonth and date.  Dates SHALL be valid dates."
        }


class dateTimeModel(BaseModel):
    dateTime: str = Field(pattern=r'^([0-9]([0-9]([0-9][1-9]|[1-9]0)|[1-9]00)|[1-9]000)(-(0[1-9]|1[0-2])(-(0[1-9]|[1-2][0-9]|3[0-1])(T([01][0-9]|2[0-3]):[0-5][0-9]:([0-5][0-9]|60)(\.[0-9]{1,9})?)?)?(Z|(\+|-)((0[0-9]|1[0-3]):[0-5][0-9]|14:00)?)?)?$')

    class Config:
        schema_extra = {
            "description": "A date, date-time or partial date (e.g. just year or year + month).  If hours and minutes are specified, a UTC offset SHALL be populated. The format is a union of the schema types gYear, gYearMonth, date and dateTime. Seconds must be provided due to schema type constraints but may be zero-filled and may be ignored.                 Dates SHALL be valid dates."
        }


class decimalModel(BaseModel):
    decimal: float = Field(pattern=r'^-?(0|[1-9][0-9]{0,17})(\.[0-9]{1,17})?([eE][+-]?[0-9]{1,9}})?$')

    class Config:
        schema_extra = {
            "description": "A rational number with implicit precision"
        }


class idModel(BaseModel):
    id: str = Field(pattern=r'^[A-Za-z0-9\-\.]{1,64}$')

    class Config:
        schema_extra = {
            "description": "Any combination of letters, numerals, - and ., with a length limit of 64 characters.  (This might be an integer, an unprefixed OID, UUID or any other identifier pattern that meets these constraints.)  Ids are case-insensitive."
        }


class instantModel(BaseModel):
    instant: str = Field(pattern=r'^([0-9]([0-9]([0-9][1-9]|[1-9]0)|[1-9]00)|[1-9]000)-(0[1-9]|1[0-2])-(0[1-9]|[1-2][0-9]|3[0-1])T([01][0-9]|2[0-3]):[0-5][0-9]:([0-5][0-9]|60)(\.[0-9]{1,9})?(Z|(\+|-)((0[0-9]|1[0-3]):[0-5][0-9]|14:00))$')

    class Config:
        schema_extra = {
            "description": "An instant in time - known at least to the second"
        }


class integerModel(BaseModel):
    integer: float = Field(pattern=r'^[0]|[-+]?[1-9][0-9]*$')

    class Config:
        schema_extra = {
            "description": "A whole number"
        }


class integer64Model(BaseModel):
    integer64: str = Field(pattern=r'^[0]|[-+]?[1-9][0-9]*$')

    class Config:
        schema_extra = {
            "description": "A very large whole number"
        }


class markdownModel(BaseModel):
    markdown: str = Field(pattern=r'^^[\s\S]+$$')

    class Config:
        schema_extra = {
            "description": "A string that may contain Github Flavored Markdown syntax for optional processing by a mark down presentation engine"
        }


class oidModel(BaseModel):
    oid: str = Field(pattern=r'^urn:oid:[0-2](\.(0|[1-9][0-9]*))+$')

    class Config:
        schema_extra = {
            "description": "An OID represented as a URI"
        }


class positiveIntModel(BaseModel):
    positiveInt: Annotated[int, Field(strict=True, gt=0)]

    class Config:
        schema_extra = {
            "description": "An integer with a value that is positive (e.g. >0)"
        }


class stringModel(BaseModel):
    string: str = Field(pattern=r'^^[\s\S]+$$')

    class Config:
        schema_extra = {
            "description": "A sequence of Unicode characters"
        }


class timeModel(BaseModel):
    time: str = Field(pattern=r'^([01][0-9]|2[0-3]):[0-5][0-9]:([0-5][0-9]|60)(\.[0-9]{1,9})?$')

    class Config:
        schema_extra = {
            "description": "A time during the day, with no date specified"
        }


class unsignedIntModel(BaseModel):
    unsignedInt: float = Field(pattern=r'^[0]|([1-9][0-9]*)$')

    class Config:
        schema_extra = {
            "description": "An integer with a value that is not negative (e.g. >= 0)"
        }


class uriModel(BaseModel):
    uri: str = Field(pattern=r'^\S*$')

    class Config:
        schema_extra = {
            "description": "String of characters used to identify a name or a resource"
        }


class urlModel(BaseModel):
    url: str = Field(pattern=r'^\S*$')

    class Config:
        schema_extra = {
            "description": "A URI that is a literal reference"
        }


class uuidModel(BaseModel):
    uuid: str = Field(pattern=r'^urn:uuid:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')

    class Config:
        schema_extra = {
            "description": "A UUID, represented as a URI"
        }


# TODO: Rename to primitives and move the models below to a separate file called General-purpose data types
class ExtensionModel(BaseModel):
    id_field: stringModel = Field(default=None, alias="id", description="Unique id for the element within a resource (for internal references). This may be any string value that does not contain spaces.")
    extension_field: List[ExtensionModel] = Field(default_factory=list, alias="extension", description="May be used to represent additional information that is not part of the basic definition of the element. To make the use of extensions safe and managable, there is a strict set of governance applied to the definition and use of extensions. Though any implementer can define an extension, there is a set of requirements that SHALL be met as part of the definition of the extension.")
    url_field: uriModel = Field(default=None, alias="url", description="Source of the definition for the extension code - a logical name or a URL.")


class PeriodModel(BaseModel):
    id_field: stringModel = Field(default=None, alias="id", description="Unique id for the element within a resource (for internal references). This may be any string value that does not contain spaces.")
    extension_field: List[ExtensionModel] = Field(default_factory=list, alias="extension", description="May be used to represent additional information that is not part of the basic definition of the element. To make the use of extensions safe and managable, there is a strict set of governance applied to the definition and use of extensions. Though any implementer can define an extension, there is a set of requirements that SHALL be met as part of the definition of the extension.")
    start_field: dateTimeModel = Field(default=None, alias="start", description="The start of the period. The boundary is inclusive.")
    end_field: dateTimeModel = Field(default=None, alias="end", description="The end of the period. If the end of the period is missing, it means no end was known or planned at the time the instance was created. The start may be in the past, and the end date in the future, which means that period is expected/planned to end at that time.")


class IdentifierModel(BaseModel):
    id_field: stringModel = Field(default=None, alias="id", description="Unique id for the element within a resource (for internal references). This may be any string value that does not contain spaces.")
    extension_field: List[ExtensionModel] = Field(default_factory=list, alias="extension", description="May be used to represent additional information that is not part of the basic definition of the element. To make the use of extensions safe and managable, there is a strict set of governance applied to the definition and use of extensions. Though any implementer can define an extension, there is a set of requirements that SHALL be met as part of the definition of the extension.")
    # Identifier_use_field: useModel = Field(..., alias="use", description="The purpose of this identifier.")
    type_field: CodeableConceptModel = Field(default=None, alias="type", description="A coded type for the identifier that can be used to determine which identifier to use for a specific purpose.")
    system_field: uriModel = Field(default=None, alias="system", description="Establishes the namespace for the value - that is, an absolute URL that describes a set values that are unique.")
    value_field: stringModel = Field(default=None, alias="value", description="The portion of the identifier typically relevant to the user and which is unique within the context of the system.")
    period_field: PeriodModel = Field(default=None, alias="period", description="Time period during which identifier is/was valid for use.")
    assigner_field: ReferenceModel = Field(default=None, alias="assigner", description="Organization that issued/manages the identifier.")


class CodingModel(BaseModel):
    id_field: stringModel = Field(default=None, alias="id", description="Unique id for the element within a resource (for internal references). This may be any string value that does not contain spaces.")
    extension_field: List[ExtensionModel] = Field(default_factory=list, alias="extension", description="May be used to represent additional information that is not part of the basic definition of the element. To make the use of extensions safe and managable, there is a strict set of governance applied to the definition and use of extensions. Though any implementer can define an extension, there is a set of requirements that SHALL be met as part of the definition of the extension.")
    system_field: uriModel = Field(default=None, alias="system", description="The identification of the code system that defines the meaning of the symbol in the code.")
    version_field: stringModel = Field(default=None, alias="version", description="The version of the code system which was used when choosing this code. Note that a well-maintained code system does not need the version reported, because the meaning of codes is consistent across versions. However this cannot consistently be assured, and when the meaning is not guaranteed to be consistent, the version SHOULD be exchanged.")
    code_field: codeModel = Field(default=None, alias="code", description="A symbol in syntax defined by the system. The symbol may be a predefined code or an expression in a syntax defined by the coding system (e.g. post-coordination).")
    display_field: stringModel = Field(default=None, alias="display", description="A representation of the meaning of the code in the system, following the rules of the system.")
    userSelected_field: booleanModel = Field(default=None, alias="userSelected", description="Indicates that this coding was chosen by a user directly - e.g. off a pick list of available items (codes or displays).")


class CodeableConceptModel(BaseModel):
    id_field: stringModel = Field(default=None, alias="id", description="Unique id for the element within a resource (for internal references). This may be any string value that does not contain spaces.")
    extension_field: List[ExtensionModel] = Field(default_factory=list, alias="extension", description="May be used to represent additional information that is not part of the basic definition of the element. To make the use of extensions safe and managable, there is a strict set of governance applied to the definition and use of extensions. Though any implementer can define an extension, there is a set of requirements that SHALL be met as part of the definition of the extension.")
    coding_field: List[CodingModel] = Field(default_factory=list, alias="coding", description="A reference to a code defined by a terminology system.")
    text_field: stringModel = Field(default=None, alias="text", description="A human language representation of the concept as seen/selected/uttered by the user who entered the data and/or which represents the intended meaning of the user.")


class ReferenceModel(BaseModel):
    id_field: stringModel = Field(default=None, alias="id", description="Unique id for the element within a resource (for internal references). This may be any string value that does not contain spaces.")
    extension_field: List[ExtensionModel] = Field(default_factory=list, alias="extension", description="May be used to represent additional information that is not part of the basic definition of the element. To make the use of extensions safe and managable, there is a strict set of governance applied to the definition and use of extensions. Though any implementer can define an extension, there is a set of requirements that SHALL be met as part of the definition of the extension.")
    reference_field: stringModel = Field(default=None, alias="reference", description="A reference to a location at which the other resource is found. The reference may be a relative reference, in which case it is relative to the service base URL, or an absolute URL that resolves to the location where the resource is found. The reference may be version specific or not. If the reference is not to a FHIR RESTful server, then it should be assumed to be version specific. Internal fragment references (start with '#') refer to contained resources.")
    type_field: uriModel = Field(default=None, alias="type", description="The expected type of the target of the reference. If both Reference.type and Reference.reference are populated and Reference.reference is a FHIR URL, both SHALL be consistent.")
    identifier_field: IdentifierModel = Field(default=None, alias="identifier", description="An identifier for the target resource. This is used when there is no way to reference the other resource directly, either because the entity it represents is not available through a FHIR server, or because there is no way for the author of the resource to convert a known identifier to an actual location. There is no requirement that a Reference.identifier point to something that is actually exposed as a FHIR instance, but it SHALL point to a business concept that would be expected to be exposed as a FHIR instance, and that instance would need to be of a FHIR resource type allowed by the reference.")
    display_field: stringModel = Field(default=None, alias="display", description="Plain text narrative that identifies the resource in addition to the resource reference.")
