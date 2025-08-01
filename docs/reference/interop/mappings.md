# Mappings

Mapping tables are used to translate between different healthcare terminology systems, code sets, and formats. These mappings are essential for semantic interoperability between CDA, HL7v2, and FHIR formats where the same concept may be represented differently.

## Mapping Types

The system supports several types of mappings:

| Mapping Type | Description | Example |
|--------------|-------------|---------|
| **Code Systems** | Maps between URI-based systems (FHIR) and OID-based systems (CDA) | SNOMED CT: `http://snomed.info/sct` ↔ `2.16.840.1.113883.6.96` |
| **Status Codes** | Maps status codes between formats | `active` ↔ `55561003` |
| **Severity Codes** | Maps severity designations between formats | `moderate` ↔ `6736007` |

## Mapping Directory Structure

Mappings are stored in YAML files in the `configs/mappings/` directory, organized by the formats they translate between:

```
configs/mappings/
├── cda_fhir/
│   ├── systems.yaml
│   ├── status_codes.yaml
│   └── severity_codes.yaml
├── hl7v2_fhir/
│   └── ...
└── README.md
```

## Mapping File Format

### Code Systems Mapping

The `systems.yaml` file maps between FHIR URI-based code systems and CDA OID-based systems:

```yaml
# mappings/cda_fhir/systems.yaml
systems:
  "http://snomed.info/sct":
    oid: "2.16.840.1.113883.6.96"
    name: "SNOMED CT"

  "http://loinc.org":
    oid: "2.16.840.1.113883.6.1"
    name: "LOINC"

  "http://www.nlm.nih.gov/research/umls/rxnorm":
    oid: "2.16.840.1.113883.6.88"
    name: "RxNorm"
```

### Status Codes Mapping

The `status_codes.yaml` file maps between different formats' status codes:

```yaml
# mappings/cda_fhir/status_codes.yaml
# Clinical status codes (CDA to FHIR)
"55561003":
  code: "active"
  display: "Active"

"73425007":
  code: "inactive"
  display: "Inactive"

"413322009":
  code: "resolved"
  display: "Resolved"
```

### Severity Codes Mapping

The `severity_codes.yaml` file maps severity designations between formats:

```yaml
# mappings/cda_fhir/severity_codes.yaml
# Allergy and reaction severity codes (CDA to FHIR)
"255604002":  # Mild (SNOMED CT)
  code: "mild"
  display: "Mild"

"6736007":  # Moderate (SNOMED CT)
  code: "moderate"
  display: "Moderate"

"24484000":  # Severe (SNOMED CT)
  code: "severe"
  display: "Severe"
```

## Using Mappings

The `InteropEngine` automatically loads and applies mappings during the conversion process. You can also access mappings directly through the configuration manager:

```python
from healthchain.interop import create_interop

# Create an engine
engine = create_interop()

# Get all mappings
mappings = engine.config.get_mappings()

# Access specific mapping
systems = mappings.get("cda_fhir", {}).get("systems", {})
snomed = systems.get("http://snomed.info/sct", {})
snomed_oid = snomed.get("oid")  # "2.16.840.1.113883.6.96"
```

## Template Filters for Mappings

The mapping system provides several Liquid template filters to help with code translation:

| Filter | Description | Example Usage |
|--------|-------------|---------------|
| `map_system` | Maps between CDA and FHIR code systems | `{{ "http://snomed.info/sct" | map_system: 'fhir_to_cda' }}` |
| `map_status` | Maps between CDA and FHIR status codes | `{{ "active" | map_status: 'fhir_to_cda' }}` |
| `map_severity` | Maps between CDA and FHIR severity codes | `{{ "moderate" | map_severity: 'fhir_to_cda' }}` |

Example in a template:

```liquid
{
  "code": {
    "@codeSystem": "{{ resource.code.coding[0].system | map_system: 'fhir_to_cda' }}",
    "@code": "{{ resource.code.coding[0].code }}"
  }
}
```

## Adding Custom Mappings

To add new mappings:

1. Create or modify the appropriate YAML file in the `configs/mappings/` directory
2. Follow the structure of existing mapping files
3. The changes will be automatically loaded the next time the `InteropEngine` is initialized

For more complex mapping needs, you can create custom mapping filters:

```python
def custom_map_filter(value, mappings, direction="fhir_to_cda"):
    # Custom mapping logic here
    return mapped_value

# Register with the template registry
engine.template_registry.add_filter("custom_map", custom_map_filter)
```

<!-- ## Best Practices

1. **Maintain Standard Terminology**: When possible, use standard terminology systems like SNOMED CT, LOINC, and RxNorm.
2. **Document Source**: Include references to the source of mapping definitions in comments.
3. **Handle Missing Mappings**: Always include logic to handle cases where mappings are not found.
4. **Test Bidirectional Mappings**: Ensure that mappings work correctly in both directions.
5. **Version Control**: Consider adding version information for terminology systems. -->

## Related Documentation

- [Configuration Management](configuration.md)
- [Templates](templates.md)
- [Custom Filters](templates.md#custom-template-filters)
