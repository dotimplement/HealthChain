# HealthChain Mappings

This directory contains mapping configurations used by the HealthChain interoperability module to translate between different healthcare data formats.

## Organization

The mappings are organized by the formats they translate between:

- `cda_default/` - Default mappings for CDA format
  - `systems.yaml` - Code system mappings (SNOMED CT, LOINC, etc.)
  - `status_codes.yaml` - Status code mappings (active, inactive, resolved)
  - `severity_codes.yaml` - Severity code mappings (mild, moderate, severe)


## Configuration

The mapping directory to use is configurable through the `defaults.mappings_dir` configuration value. The default is `"cda_default"`.

## Structure

Each mapping file uses a flat structure designed for clarity and simplicity. See the README in each subdirectory for detailed examples and documentation.

## Adding New Mappings

To add mappings for new format combinations:

1. Create a new subdirectory (e.g., `hl7v2/` for HL7v2 mappings, or `cda_local/` for local CDA mappings)
2. Add yaml files for each mapping type needed
3. Update the mapping directory in your configuration to use the new mappings

## Usage

These mapping files are loaded automatically by the `InteropConfigManager` and are used by the filters in the `healthchain.interop.filters` module to translate codes between formats.
