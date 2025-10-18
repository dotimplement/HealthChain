# Experimental Templates

This page tracks templates that are under development or have known issues. Use these at your own risk and please contribute fixes!

## Template Status

| Template Type | Status | Known Issues | Location |
|---------------|--------|--------------|----------|
| **Problems** | 🟢 **Basic Stable** | None, but not fully tested for edge cases | Bundled in default configs |
| **Medications** | 🟢 **Basic Stable** | None, but not fully tested for edge cases | Bundled in default configs |
| **Notes** | 🟢 **Basic Stable** | None, but not fully tested for edge cases, html tags are parsed as text | Bundled in default configs |
| **Allergies** | ⚠️ **Experimental** | Clinical status parsing bugs, round-trip issues | `dev-templates/allergies/` |

## Using Experimental Templates

### Allergies (AllergyIntolerance)

**Status:** ⚠️ Experimental - Known bugs prevent inclusion in bundled configs

**Known Issues:**
- Clinical status parsing has bugs (see integration test comments)
- Round-trip conversion may not preserve all data correctly
- Template logic is fragile and may fail with edge cases

**Location:** `dev-templates/allergies/`

**Usage:**

1. Copy experimental files to your custom config:
   ```bash
   # After running: healthchain init-configs my_configs
   cp dev-templates/allergies/allergies.yaml my_configs/interop/cda/sections/
   cp dev-templates/allergies/allergy_*.liquid my_configs/templates/cda_fhir/
   cp dev-templates/allergies/allergy_*.liquid my_configs/templates/fhir_cda/
   ```

2. Enable in your CCD document config:
   ```yaml
   # my_configs/interop/cda/document/ccd.yaml
   body:
     include_sections:
       - "allergies"  # Add this line
       - "medications"
       - "problems"
       - "notes"
   ```

3. **Test thoroughly** with your specific data before production use.

## Contributing Template Fixes

We welcome contributions to improve experimental templates!

### For Allergies:
- **Clinical status mapping** - The biggest issue is parsing clinical status from CDA observations
- **Round-trip fidelity** - Ensure CDA → FHIR → CDA preserves all important data
- **Edge case handling** - Make templates robust to various CDA structures

### General Guidelines:
1. **Test with real data** - Use the example CDAs in `resources/` for testing
2. **Add comprehensive tests** - Include both unit and integration tests
3. **Document limitations** - Be clear about what your fix does/doesn't solve
4. **Follow template patterns** - Keep consistent with existing stable templates

### Submitting Fixes:
1. Fix the templates in `dev-templates/`
2. Add/update tests to cover your changes
3. Move stable templates to bundled configs in your PR
4. Update this documentation

## Roadmap

**Next Priorities:**

1. 🎯 **Allergies stabilization** - Fix clinical status parsing and round-trip issues
2. 🔮 **Future sections** - Procedures, Vital Signs, Lab Results
3. 🔧 **Template tooling** - Better validation and testing framework

Want to help? Check our [contribution guidelines](../../community/contribution_guide.md) and pick up one of these challenges!
