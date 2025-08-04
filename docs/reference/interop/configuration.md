# Configuration

The interoperability module uses a configuration system to control its behavior. This includes mappings between different healthcare data formats, validation rules, and environment-specific settings.

## Configuration Overview

HealthChain works out-of-the-box with default configurations, but you can customize them for your specific needs.

### Default Usage

```python
from healthchain.interop import create_interop

# Uses bundled default configurations
engine = create_interop()
```

### Custom Configuration

```python
# Use custom config directory
engine = create_interop(config_dir="/path/to/custom/configs")
```

### Creating Custom Configs

To create editable configuration templates:

```bash
# Create customizable config templates
healthchain init-configs ./my_configs

# Then use them in your code
engine = create_interop(config_dir="./my_configs")
```

This gives you editable copies of:
- **Templates**: CDA ↔ FHIR conversion templates
- **Mappings**: Code system mappings (SNOMED, LOINC, etc.)
- **Validation**: Schema validation rules
- **Environment settings**: Development, testing, production configs

## Configuration Components

| Component | Description |
|-----------|-------------|
| `InteropConfigManager` | Manages access to configuration files and values |
| `defaults.yaml` | Default configuration values for FHIR required fields |
| `environments/` | Environment-specific configuration values |
| `interop/` | Configuration for format specific settings (e.g. CDA, HL7v2) |
| `mappings/` | Mapping tables for codes, identifiers, and terminology systems |
| `templates/` | Templates for generating healthcare documents |

## Configuration Structure

The configuration system uses `YAML` files with a hierarchical structure. The main configuration sections include:

- `defaults`: Global default values
- `cda`: Contains CDA specific configurations
    - `sections`: Configuration for CDA document sections
    - `document`: Configuration for CDA document types
- `mappings`: Mappings between different terminology systems
- `templates`: Template configuration

## Default Configuration

The default configuration is stored in `configs/defaults.yaml` and contains global settings and default fallback values for required fields in FHIR resources in the event that they are not provided in the source document.

```yaml
defaults:
  # Common defaults for all resources
  common:
    id_prefix: "hc-"
    timestamp: "%Y%m%d"
    reference_name: "#{uuid}name"
    subject:
      reference: "Patient/example"

  # Resource-specific defaults
  resources:
    Condition:
      clinicalStatus:
        coding:
          - system: "http://terminology.hl7.org/CodeSystem/condition-clinical"
            code: "unknown"
            display: "Unknown"
    MedicationStatement:
      status: "unknown"
      medication:
        concept:
          coding:
            - system: "http://terminology.hl7.org/CodeSystem/v3-NullFlavor"
              code: "UNK"
              display: "Unknown"
```

## CDA Configurations

CDA configurations primarily concern the extraction and rendering processes on the ***document*** and ***section*** level. While [Templates](./templates.md) are used to define the syntactic structure of the document, the YAML configurations are used to define the semantic content of the document structure, such as template IDs, status codes, and other metadata.

Configs are loaded from the `configs/interop/cda/` directory and loaded in the `ConfigManager` with the folder and filenames as keys. e.g. given the following directory structure:

```
configs/
  interop/
    cda/
      document/
        ccd.yaml
      sections/
        problems.yaml
```
The config will be loaded into the config manager under the key `cda.document.ccd` and `cda.sections.problems`.

### Example Document Configuration

```yaml
# configs/interop/cda/document/ccd.yaml

# Configured template names in templates/ directory (required)
templates:
  document: "fhir_cda/document"
  section: "fhir_cda/section"

# Basic document information
code:
  code: "34133-9"
  code_system: "2.16.840.1.113883.6.1"
  code_system_name: "LOINC"
  display: "Summarization of Episode Note"
realm_code: "GB"
type_id:
  extension: "POCD_HD000040"
  root: "2.16.840.1.113883.1.3"
template_id:
  root: "1.2.840.114350.1.72.1.51693"
# ...

# Document structure
structure:
  # Header configuration
  header:
    include_patient: false
    include_author: false
    include_custodian: false

  # Body configuration
  body:
    structured_body: true
    non_xml_body: false
    include_sections:
      - "allergies"
      - "medications"
      - "problems"
```

### Example Section Configuration

```yaml
# configs/interop/cda/sections/problems.yaml

# Metadata for both extraction and rendering processes (required)
resource: "Condition" # The FHIR resource this section maps to
resource_template: "cda_fhir/condition" # The template to use for the FHIR resource rendering
entry_template: "fhir_cda/problem_entry" # The template to use for the CDA section entry rendering

# Section identifiers (used for extraction) (required)
identifiers:
  template_id: "2.16.840.1.113883.10.20.1.11"
  code: "11450-4"

# Template configuration (used for rendering)
template:
  act:
    template_id:
      - "2.16.840.1.113883.10.20.1.27"
    status_code: "completed"
    # ...
```

## Mapping Tables

Mapping tables are used to translate codes and identifiers between different terminology systems. These are stored in the `mappings/` directory.

Example mapping table for coding systems:

```yaml
# mappings/cda_default/systems.yaml
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
(Full Documentation on [Mappings](mappings.md))


## Environment-Specific Configuration

The configuration system supports different environments (development, testing, production) with environment-specific overrides. These are stored in the `environments/` directory. In development and subject to change.

```yaml
# environments/development.yaml
defaults:
  common:
    id_prefix: "dev-"     # Development-specific ID prefix
    subject:
      reference: "Patient/Foo"

# environments/production.yaml
defaults:
  common:
    id_prefix: "hc-"      # Production ID prefix
    subject:
      reference: "Patient/example"
```

## Using the Configuration Manager

### Basic Configuration Access

```python
from healthchain.interop import create_interop

# Create an engine
engine = create_interop()
# OR
engine = create_interop(config_dir="custom_configs/")

# Get all configurations
engine.config.get_configs()

# Get a configuration value by dot notation
id_prefix = engine.config.get_config_value("defaults.common.id_prefix")

# Set the environment (this reloads configuration from the specified environment)
engine = create_interop(environment="production")

# Validation level is set during initialization or using set_validation_level
engine = create_interop(validation_level="warn")
# OR
engine.config.set_validation_level("strict")

# Set a runtime configuration override
engine.config.set_config_value("cda.sections.problems.identifiers.code", "10160-0")
```

### Section Configuration

```python
from healthchain.interop import create_interop

# Create an engine
engine = create_interop()

# Get all section configurations
sections = engine.config.get_cda_section_configs()

# Get a specific section configuration
problems_config = engine.config.get_cda_section_configs("problems")

# Get section identifiers
template_id = problems_config["identifiers"]["template_id"]
code = problems_config["identifiers"]["code"]
```

### Mapping Access

```python
from healthchain.interop import create_interop

# Create an engine
engine = create_interop()

# Get all mappings
mappings = engine.config.get_mappings()

# Get a specific mapping
systems = mappings.get("cda_fhir", {}).get("systems", {})
snomed = systems.get("http://snomed.info/sct", {})
snomed_oid = snomed.get("oid")  # "2.16.840.1.113883.6.96"
```

## Configuration Precedence

Configuration values are loaded in order of precedence:

1. **Base configuration** (defaults.yaml) - lowest precedence
2. **Environment configuration** (environments/{env}.yaml) - overrides defaults
3. **Runtime overrides** (via API) - highest precedence

```python
# Example: Override configuration at runtime
engine = create_interop()
engine.config.set_config_value("defaults.common.id_prefix", "custom-")
```

## Validation Levels

The configuration system supports different validation levels:

| Level | Description |
|-------|-------------|
| `strict` | Raise exceptions for any configuration errors |
| `warn` | Log warnings for configuration errors but continue |
| `ignore` | Ignore configuration errors |

```python
from healthchain.interop import create_interop

# Create an engine with a specific validation level
engine = create_interop(validation_level="warn")

# Change the validation level
engine.config.set_validation_level("strict")
```
