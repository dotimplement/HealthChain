# Experimental Allergy Templates

⚠️ **Warning: These templates are experimental and contain known bugs.**

This directory contains allergy-related configuration and templates that were removed from the default bundled configs due to reliability issues.

📖 **For full documentation on experimental templates, see:** [docs/reference/interop/experimental.md](../docs/reference/interop/experimental.md)

## Contents

- `allergies.yaml` - Section configuration for allergy processing
- `allergy_entry.liquid` - Template for converting FHIR AllergyIntolerance to CDA
- `allergy_intolerance.liquid` - Template for converting CDA allergies to FHIR

## Known Issues

- Clinical status parsing has bugs (see integration test comments)
- Round-trip conversion may not preserve all data correctly
- Template logic is fragile and may fail with edge cases

## Usage

If you need allergy support despite the bugs:

1. Copy these files to your custom config directory:
   ```bash
   # After running: healthchain init-configs my_configs
   cp cookbook/experimental_templates/allergies/* my_configs/interop/cda/sections/
   cp cookbook/experimental_templates/allergies/allergy_*.liquid my_configs/templates/cda_fhir/
   cp cookbook/experimental_templates/allergies/allergy_*.liquid my_configs/templates/fhir_cda/
   ```

2. Add "allergies" to your CCD document config:
   ```yaml
   # my_configs/interop/cda/document/ccd.yaml
   body:
     include_sections:
       - "allergies"  # Add this
       - "medications"
       - "problems"
       - "notes"
   ```

3. Test thoroughly with your specific data before using in production.

## Contributing

If you fix the bugs in these templates, please consider contributing back to the main project!
