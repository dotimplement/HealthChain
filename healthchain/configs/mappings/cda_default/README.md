# CDA Default Mappings

This directory contains default mapping configurations used to translate between CDA (Clinical Document Architecture) and FHIR (Fast Healthcare Interoperability Resources) formats.

## Files

- `systems.yaml` - Code system mappings between FHIR URLs and CDA OIDs
- `status_codes.yaml` - Status code mappings (FHIR status codes to CDA status codes)
- `severity_codes.yaml` - Severity code mappings (FHIR severity codes to CDA severity codes)

## Structure

Each mapping file uses a flat structure designed for clarity and simplicity, consistently using FHIR values as keys mapping to CDA values:

### systems.yaml
```yaml
"http://snomed.info/sct":
  oid: "2.16.840.1.113883.6.96"
  name: "SNOMED CT"

"http://loinc.org":
  oid: "2.16.840.1.113883.6.1"
  name: "LOINC"
```

### status_codes.yaml
```yaml
"active":
  code: "55561003"
  display: "Active"

"resolved":
  code: "413322009"
  display: "Resolved"
```

### severity_codes.yaml
```yaml
"severe":
  code: "H"
  display: "Severe"

"moderate":
  code: "M"
  display: "Moderate"
```

## Usage

These mappings are used by the filters in the interoperability module for bidirectional translation between CDA and FHIR:

1. **FHIR to CDA**: Maps FHIR URLs to CDA OIDs, FHIR status codes to CDA status codes, etc.
2. **CDA to FHIR**: Maps CDA OIDs to FHIR URLs, CDA status codes to FHIR status codes, etc. (reverse lookup)
