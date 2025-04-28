# Working with xmltodict in HealthChain

The HealthChain interoperability engine uses [xmltodict](https://github.com/martinblech/xmltodict) to convert between XML and Python dictionaries. This guide explains key conventions to be aware of when working with the parsed data.

*Why use `xmltodict`?* You say, *Why not use the `lxml` or `xml.etree.ElementTree` or some other decent library so you can work on the XML tree directly?*

There are two main reasons:

- HealthChain uses [Pydantic](https://docs.pydantic.dev/) models for validation and type checking extensively, which works best with JSON-able data. We wanted to keep everything in modern Python ecosystem whilst still being able to work with XML, which is still a very common format in healthcare

- Developer experience: it's just easier to work with JSON than XML trees in Python 🤷‍♀️

The flow roughly looks like this:

```bash
XML ↔ Dictionary with @ prefixes ↔ Pydantic Model
```

Still with me? Cool. Let's dive into the key conventions to be aware of when working with the parsed data.

## Key Conventions

### Attribute Prefixes
XML attributes are prefixed with `@`:
```xml
<code code="55607006" displayName="Problem"/>
```
becomes:
```python
{
    "code": {
        "@code": "55607006",
        "@displayName": "Problem"
    }
}
```

### Text Content
Text content of elements is represented with `#text`:
```xml
<displayName>Hypertension</displayName>
```
becomes:
```python
{
    "displayName": "Hypertension"
}
```
or for mixed content:
```xml
<text>Some <b>bold</b> text</text>
```
becomes:
```python
{
    "text": {
        "#text": "Some  text",
        "b": "bold"
    }
}
```

### Lists vs Single Items
A collection of elements with the same name becomes a list:
```xml
<component>
  <section>...</section>
</component>
<component>
  <section>...</section>
</component>
```
becomes:
```python
{
    "component": [
        {"section": {...}},
        {"section": {...}}
    ]
}
```

### Force List Parameter
When parsing, you can force certain elements to always be lists even when there's only one:
```python
xmltodict.parse(xml_string, force_list=('component', 'entry'))
```

### Namespaces
Namespaces are included in element names:
```xml
<ns1:element xmlns:ns1="http://example.org">value</ns1:element>
```
becomes:
```python
{
    "ns1:element": {
        "@xmlns:ns1": "http://example.org",
        "#text": "value"
    }
}
```

## Tips for Working with CDA Documents

- Remember to use the `@` prefix for attributes
- Always check if an element might be a list before accessing it directly
- In Liquid, use `['string']` to access attributes with `@` prefixes. e.g. `act.entry.code['@code']`
- When generating XML, make sure to include required namespaces
