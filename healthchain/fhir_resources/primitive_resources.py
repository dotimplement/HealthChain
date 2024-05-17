from __future__ import annotations

from pydantic import conint
from pydantic import constr


booleanModel = constr(pattern=r"^(true|false)$")
canonicalModel = constr(pattern=r"^\S*$")
codeModel = constr(pattern=r"^[^\s]+( [^\s]+)*$")
comparatorModel = constr(pattern="^(<|<=|>=|>)$")
dateModel = constr(
    pattern=r"^([0-9]([0-9]([0-9][1-9]|[1-9]0)|[1-9]00)|[1-9]000)(-(0[1-9]|1[0-2])(-(0[1-9]|[1-2][0-9]|3[0-1]))?)?$"
)
dateTimeModel = constr(
    pattern=r"^([0-9]([0-9]([0-9][1-9]|[1-9]0)|[1-9]00)|[1-9]000)(-(0[1-9]|1[0-2])(-(0[1-9]|[1-2][0-9]|3[0-1])(T([01][0-9]|2[0-3]):[0-5][0-9]:([0-5][0-9]|60)(\.[0-9]{1,9})?)?)?(Z|(\+|-)((0[0-9]|1[0-3]):[0-5][0-9]|14:00)?)?)?$"
)
decimalModel = constr(
    pattern=r"^-?(0|[1-9][0-9]{0,17})(\.[0-9]{1,17})?([eE][+-]?[0-9]{1,9}})?$"
)
idModel = constr(pattern=r"^[A-Za-z0-9\-\.]{1,64}$")
instantModel = constr(
    pattern=r"^([0-9]([0-9]([0-9][1-9]|[1-9]0)|[1-9]00)|[1-9]000)-(0[1-9]|1[0-2])-(0[1-9]|[1-2][0-9]|3[0-1])T([01][0-9]|2[0-3]):[0-5][0-9]:([0-5][0-9]|60)(\.[0-9]{1,9})?(Z|(\+|-)((0[0-9]|1[0-3]):[0-5][0-9]|14:00))$"
)
integerModel = constr(pattern=r"^[0]|[-+]?[1-9][0-9]*$")
integer64Model = constr(pattern=r"^[0]|[-+]?[1-9][0-9]*$")
markdownModel = constr(pattern=r"^^[\s\S]+$$")
oidModel = constr(pattern=r"^urn:oid:[0-2](\.(0|[1-9][0-9]*))+$")
positiveIntModel = conint(strict=True, gt=0)
stringModel = constr(pattern=r"^^[\s\S]+$$")
timeModel = constr(
    pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]:([0-5][0-9]|60)(\.[0-9]{1,9})?$"
)
unsignedIntModel = constr(pattern=r"^[0]|([1-9][0-9]*)$")
uriModel = constr(pattern=r"^\S*$")
urlModel = constr(pattern=r"^\S*$")
uuidModel = constr(
    pattern=r"^urn:uuid:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
