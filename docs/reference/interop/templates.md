# Templates

The HealthChain interoperability module uses a template system based on [**Liquid**](https://shopify.github.io/liquid/), an open-source templating language to generate healthcare data in various formats. This allows for flexible and customizable document generation on a syntactic level.

## Template Directory Structure

Templates are stored in the `configs/templates` directory by default. The directory structure follows a convention based on format and resource type:

```
templates/
├── cda_fhir/
│   ├── document.liquid
│   ├── section.liquid
│   ├── problem_entry.liquid
│   ├── medication_entry.liquid
│   └── allergy_entry.liquid
├── cda_fhir/
│   ├── condition.liquid
│   ├── medication_statement.liquid
│   └── allergy_intolerance.liquid
├── hl7v2_fhir/
│   ├── adt_a01.liquid
│   ├── oru_r01.liquid
│   └── obx_r01.liquid
├── fhir_hl7v2/
│   ├── patient_adt.liquid
│   ├── encounter_adt.liquid
│   └── observation_oru.liquid
```
Templates can be accessed through the `TemplateRegistry`:

1. Using their full path within the template directory without extension as a key: `cda_fhir/document`
2. Using just their stem name as a key: `document`

Using full paths is recommended for clarity and to avoid confusion when templates with the same filename exist in different directories. However, both methods will work as long as template names are unique across all directories and matches the template name in the configuration files.

## Default Templates

HealthChain provides default templates for the transformation of Problems, Medications, and Notes sections in a Continuity of Care (CCD) CDA to FHIR and the reverse. They are configured to work out of the box with the default configuration and the example CDAs [here](https://github.com/dotimplement/HealthChain/tree/main/resources).

You are welcome to modify these templates at your own discretion or use them as a starting reference point for your writing your own templates. **Always verify that templates work for your use case.**

**Note:** Some templates are experimental and not included in the default configs. See [Experimental Templates](experimental.md) for details on templates under development.

| CDA Section | FHIR Resource |
|-------------|---------------|
| **Problems** | [**Condition**](https://www.hl7.org/fhir/condition.html) |
| **Medications** | [**MedicationStatement**](https://www.hl7.org/fhir/medicationstatement.html) |
| **Notes** | [**DocumentReference**](https://www.hl7.org/fhir/documentreference.html) |

CDA to FHIR templates:

| CDA Section | Default Template |
|-------------|------------------|
| **Problems** | `fhir_cda/problem_entry.liquid` |
| **Medications** | `fhir_cda/medication_entry.liquid` |
| **Notes** | `fhir_cda/note_entry.liquid` |

FHIR to CDA templates:

| Resource Type | Default Template |
|---------------|------------------|
| **Condition** | `cda_fhir/condition.liquid` |
| **MedicationStatement** | `cda_fhir/medication_statement.liquid` |
| **DocumentReference** | `cda_fhir/document_reference.liquid` |

## Template Format

Templates use Python [**Liquid**](https://liquid.readthedocs.io/en/latest/) syntax with additional custom filters provided by the interoperability module. Note that HealthChain uses [**xmltodict**](https://github.com/martinblech/xmltodict) to parse and unparse XML documents into dictionaries and vice versa, therefore templates should be written in JSON format that is compatible with `xmltodict`. For more information, see the [Working with xmltodict in HealthChain](./xmltodict.md) guide (it's not that bad, I promise).

Example template for a CDA to FHIR conversion:

```liquid
{
  "act": {
    "@classCode": "ACT",
    "@moodCode": "EVN",
    "templateId": [
    {% for template_id in config.template.act.template_id %}
      {"@root": "{{template_id}}"} {% if forloop.last != true %},{% endif %}
    {% endfor %}
    ],
    {% if resource.id %}
    "id": {"@root": "{{ resource.id }}"},
    {% endif %}
    "code": {"@nullFlavor": "NA"},
    "statusCode": {
      "@code": "{{ config.template.act.status_code }}"
    }
  }
}
```

## Using the Template System

### Interoperability Engine API

The Interoperability Engine API provides a high-level interface (`.to_fhir()` and `.from_fhir()`) for transforming healthcare data between different formats using templates.

```python
from healthchain.interop import create_interop, FormatType
from healthchain.fhir import create_condition

# Create an engine
engine = create_interop()

# Create a FHIR resource
condition = create_condition(
  code="38341003",
  system="http://snomed.info/sct",
  display="Hypertension",
  subject="Patient/123",
  clinical_status="active"
)

# Generate CDA from FHIR resources
cda_xml = engine.from_fhir([condition], dest_format=FormatType.CDA)

# Generate FHIR from CDA
fhir_resources = engine.to_fhir(cda_xml, src_format=FormatType.CDA)
```

### Direct Template Access (Advanced)

For advanced use cases, you can access the template system directly:

```python
from healthchain.interop import create_interop

# Create an engine
engine = create_interop()

# Access the template registry
registry = engine.template_registry

# Get a template by name
template = registry.get_template("cda_fhir/condition")
```

## Creating Custom Templates

To create a custom template:

1. Create a new file in the appropriate template directory. Use a descriptive name for the template, e.g. `cda_fhir/procedure.liquid`.
2. Create a template using Python Liquid syntax with available filters if needed.
3. Access source data properties using dot notation. (e.g. `entry.act.id`)
4. Access configuration values (see [Configuration](./configuration.md)) using the `config` object.

For example, to create a custom template to transform a CDA section into a FHIR Procedure resource:

```liquid
<!-- configs/templates/cda_fhir/procedure.liquid -->
{
  "procedure": {
    "@classCode": "PROC",
    "@moodCode": "EVN",
    "templateId": {
      "@root": "2.16.840.1.113883.10.20.1.29"
    },
    "id": {
      "@root": "{{ entry.act.id | generate_id }}"
    },
    "code": {
      "@code": "{{ entry.act.entryRelationship.observation.value['@code'] }}",
      "@displayName": "{{ entry.act.entryRelationship.observation.value['@displayName'] }}",
      "@codeSystem": "{{ entry.act.entryRelationship.observation.value['@codeSystem'] | map_system: 'fhir_to_cda' }}",
    },
    "statusCode": {
      "@code": "{{ entry.act.statusCode['@code'] | map_status: 'fhir_to_cda' }}"
    },
    "effectiveTime": {
      "@value": "{{ entry.act.effectiveTime['@value'] | format_date }}"
    },
    {% if entry.act.performer %}
    "performer": {
      "assignedEntity": {
        "id": {
          "@root": "{{ entry.act.performer[0].actor.reference }}"
        }
      }
    }
    {% endif %}
  }
}
```
## Custom Template Filters

The template system provides several custom filters for common healthcare document transformation tasks:

| Filter | Description |
|--------|-------------|
| `map_system` | Maps between CDA and FHIR code systems |
| `map_status` | Maps between CDA and FHIR status codes |
| `map_severity` | Maps between CDA and FHIR severity codes |
| `format_date` | Formats a date in the correct format for the output document |
| `format_timestamp` | Formats a timestamp or uses current time |
| `generate_id` | Generates an ID or uses provided value |
| `to_json` | Converts object to JSON string |
| `extract_effective_period` | Extracts effective period data from CDA effectiveTime elements |
| `extract_effective_timing` | Extracts timing data from effectiveTime elements |
| `extract_clinical_status` | Extracts clinical status from an observation |
| `clean_empty` | Recursively removes empty values from dictionaries and lists |
| `to_base64` | Encodes text to base64 |
| `from_base64` | Decodes base64 to text |
| `xmldict_to_html` | Converts xmltodict format to HTML string |

### Using Filters

```liquid
<!-- Map a system -->
{{ resource.code.coding[0].system | map_system: 'fhir_to_cda' }}

<!-- Base64 encoding and decoding -->
{{ "Hello World" | to_base64 }}
<!-- Outputs: SGVsbG8gV29ybGQ= -->

{{ "SGVsbG8gV29ybGQ=" | from_base64 }}
<!-- Outputs: Hello World -->

<!-- Convert XML dictionary to HTML -->
{% assign xml_dict = {'div': {'p': 'Hello', '@class': 'note'}} %}
{{ xml_dict | xmldict_to_html }}
<!-- Outputs: <div><p class="note">Hello</p></div> -->
```
For more information on using filters, see Liquid's [official documentation](https://shopify.github.io/liquid/basics/introduction/).

### Adding Custom Filters

You can add custom filters to the template system:

```python
from healthchain.interop import create_interop

def custom_filter(value):
    return f"CUSTOM:{value}"

# Create an engine
engine = create_interop()

# Add a custom filter
engine.template_registry.add_filter("custom", custom_filter)
```
