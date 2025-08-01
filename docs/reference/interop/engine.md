# InteropEngine

The `InteropEngine` is the core component of the HealthChain interoperability module. It provides a unified interface for converting between different healthcare data formats.

## Basic Usage

```python
from healthchain.interop import create_interop, FormatType

# Create an interoperability engine
engine = create_interop()

# Convert CDA XML to FHIR resources
fhir_resources = engine.to_fhir(cda_xml, src_format=FormatType.CDA)

# Convert FHIR resources to CDA XML
cda_xml = engine.from_fhir(fhir_resources, dest_format=FormatType.CDA)

# Convert HL7v2 message to FHIR resources
fhir_resources = engine.to_fhir(hl7v2_message, src_format=FormatType.HL7V2)
```

## Creating an Engine

The `create_interop()` function is the recommended way to create an engine instance:

```python
from healthchain.interop import create_interop

# Create with default configuration
engine = create_interop()
```

### Custom Configuration

```python
# Use custom config directory
engine = create_interop(config_dir="/path/to/custom/configs")

# Create with custom validation level and environment
engine = create_interop(validation_level="warn", environment="production")
```


> **💡 Tip:**
> To create editable configuration templates, run:
>
> ```bash
> healthchain init-configs ./my_configs
> ```
> This will create a `my_configs` directory with editable default configuration templates.

## Conversion Methods

All conversions convert to and from FHIR.

| Method | Description |
|--------|-------------|
| `to_fhir(data, src_format)` | Convert from source format to FHIR resources |
| `from_fhir(resources, dest_format)` | Convert from FHIR resources to destination format |

### Converting to FHIR

```python
# From CDA
fhir_resources = engine.to_fhir(cda_xml, src_format=FormatType.CDA)

# From HL7v2
fhir_resources = engine.to_fhir(hl7v2_message, src_format=FormatType.HL7V2)
```

### Converting from FHIR

```python
# To CDA
cda_xml = engine.from_fhir(fhir_resources, dest_format=FormatType.CDA)

# To HL7v2
hl7v2_message = engine.from_fhir(fhir_resources, dest_format=FormatType.HL7V2)
```

## Accessing Configuration

The engine provides direct access to the underlying configuration manager:

```python
# Access configuration directly
engine.config.set_environment("production")
engine.config.set_validation_level("warn")
value = engine.config.get_config_value("cda.sections.problems.resource")
```

## Custom Components

You can register custom parsers and generators to extend the engine's capabilities. Note that registering a custom parser / generator for an existing format type will replace the default.

```python
from healthchain.interop import FormatType

# Register a custom parser
engine.register_parser(FormatType.CDA, custom_parser)

# Register a custom generator
engine.register_generator(FormatType.FHIR, custom_generator)
```
<!--  This bit is a big confusing, maybe put it in a cookbook example to add custom stuff
### Custom Configuration Validation

You can also register Pydantic models to the engine for custom configuration validation.

The configurations are used in the Liquid templates and control the structural content of the generated document.

This is useful when you need to add additional sections to the CDA document template or would like to customize the validation of existing default sections.

```python
from healthchain.config.validators import ComponentTemplateConfig, SectionTemplateConfigBase

# Register a validator for the Procedure section, should inherit from SectionTemplateConfigBase
class ProcedureSectionConfig(SectionTemplateConfigBase):
    procedure: ComponentTemplateConfig
    specimen: ComponentTemplateConfig
    indication_obs: ComponentTemplateConfig

engine.register_cda_section_config_validator("Procedure", ProcedureSectionConfig)
```

You can also register a custom document configuration validator for different document types.

```python
from healthchain.config.validators import DocumentConfigBase

# Register a validator for the Discharge Summary document, should inherit from DocumentConfigBase
class DischargeSummaryDocumentConfig(DocumentConfigBase):
    # specific custom configs
    discharge_diagnosis: Dict[str, Any]
    discharge_medications: Dict[str, Any]

engine.register_cda_document_config_validator("DischargeSummary", DischargeSummaryDocumentConfig)
```

For more information see the [Validators API](../../api/interop.md). -->

## Advanced Configuration

For more information on the configuration options, see the [Configuration](configuration.md) page.
