# Interoperability Engine

The HealthChain Interop Engine provides a robust and customizable framework for converting between different HL7 healthcare data formats, including:

- FHIR
- CDA
- HL7v2 (Coming soon)

## Architecture

The interoperability module is built around a central `InteropEngine` that coordinates format conversion through specialized parsers and generators:

```
                    ┌───────────────┐
                    │ InteropEngine │
                    └───────┬───────┘
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
┌─────────▼─────────┐ ┌─────▼─────┐ ┌─────────▼─────────┐
│      Parsers      │ │ Templates │ │     Generators    │
└─────────┬─────────┘ └─────┬─────┘ └─────────┬─────────┘
          │                 │                 │
┌─────────▼─────────┐ ┌─────▼─────┐ ┌─────────▼─────────┐
│   - CDA Parser    │ │ Registry  │ │   - CDA Generator │
│   - HL7v2 Parser  │ │ Renderer  │ │  - FHIR Generator │
└───────────────────┘ └───────────┘ │ - HL7v2 Generator │
                                    └───────────────────┘
```

## Key Components

| Component | Description |
|-----------|-------------|
| [**InteropEngine**](engine.md) | Core engine that manages the conversion process |
| [**Templates**](templates.md) | Liquid-based template system for customizing output syntactic generation |
| [**Mappings**](mappings.md) | Mappings between different terminology systems |
| [**Configuration**](configuration.md) | Configuration system for controlling engine behavior and template variations|
| [**Parsers**](parsers.md) | Components for parsing different healthcare formats |
| [**Generators**](generators.md) | Components for generating output in different formats |

## Basic Usage

FHIR serves as the de facto modern data standard in HealthChain and in the world of healthcare more broadly, therefore everything converts to and from FHIR resources.

The main conversion methods are (hold on to your hats):

- `.to_fhir()` - Convert a source format to FHIR resources
- `.from_fhir()` - Convert FHIR resources to a destination format

```python
from healthchain.interop import create_interop, FormatType

# Create an interoperability engine
engine = create_interop()

# Convert CDA XML to FHIR resources
with open('patient_ccd.xml', 'r') as f:
    cda_xml = f.read()

fhir_resources = engine.to_fhir(cda_xml, src_format="cda")

# Convert FHIR resources back to CDA
cda_document = engine.from_fhir(fhir_resources, dest_format="cda")
```
### Custom Configs

The default templates that come with the package are limited to problems, medications, and notes and are meant for basic testing and prototyping. Use the `healthchain init-configs` command to create editable configuration templates:

```bash
# Create editable configuration templates
healthchain init-configs ./my_configs
```

Then use the `config_dir` parameter to specify the path to your custom configs:

```python
# Use your customized configs
engine = create_interop(config_dir="./my_configs")

# Now you can customize:
# • Add experimental features (allergies, procedures)
# • Modify terminology mappings (SNOMED, LOINC codes)
# • Customize templates for your organization's CDA format
# • Configure validation rules and environments
```

## Customization Points

The interoperability module is designed with extensibility at its core. You can customize and extend the framework in several ways:

### Custom Parsers

Parsers convert source formats (CDA or HL7v2) into mapped dictionaries that can be processed by generators:

```python
# Register a custom parser with the engine
engine.register_parser(FormatType.CDA, CustomCDAParser(engine.config))
```

For detailed implementation examples, see [Creating a Custom Parser](parsers.md#creating-a-custom-parser).

### Custom Generators

Generators transform mapped dictionaries into target formats:

```python
# Register a custom generator with the engine
engine.register_generator(FormatType.CDA,
                         CustomCDAGenerator(engine.config, engine.template_registry))
```

For detailed implementation examples, see [Creating a Custom Generator](generators.md#creating-a-custom-generator).


### Environment Configuration

You can customize the engine's behavior for different environments:

```python
# Create an engine with specific environment settings
engine = create_interop(
    config_dir=Path("/path/to/custom/configs"),
    validation_level="warn",  # Options: strict, warn, ignore
    environment="production"  # Options: development, testing, production
)

# Change environment settings after creation
engine.config.set_environment("testing")
engine.config.set_validation_level("strict")

# Access environment-specific configuration
id_prefix = engine.config.get_config_value("defaults.common.id_prefix")
```

Environment-specific configurations are loaded from the `environments/` directory and can override default settings for different deployment scenarios.

### Template Customization

The template system uses [Liquid templates](https://shopify.github.io/liquid/) to generate output formats. You can:

1. Override existing templates by placing custom versions in the configured template directory
2. Add new templates for custom formats or content types
3. Extend the template system with custom logic via filters

For more details on extending the system, check out the [Templates](templates.md) and [Configuration](configuration.md) pages.
