# Mappers

Mappers transform data between different healthcare formats and structures. They enable standardized data conversion workflows while maintaining clinical semantics and validation.

## Available Mappers

| Mapper | Source Format | Target Format | Primary Use Case |
|--------|---------------|---------------|------------------|
| [**FHIRFeatureMapper**](fhir_feature.md) | FHIR Bundle | pandas DataFrame | Extract ML-ready features from FHIR resources |

### Future Mappers (Planned)

- **FHIR-to-FHIR Mapper**: Transform between FHIR resource types
- **FHIR-to-OMOP Mapper**: Convert between FHIR and OMOP Common Data Model

## Related Documentation

- [Containers](../containers/containers.md) - Data containers that use mappers
- [Dataset](../containers/dataset.md) - Uses FHIRFeatureMapper for feature extraction
- [Adapters](../adapters/adapters.md) - Convert between healthcare protocols
