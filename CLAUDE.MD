# HealthChain - Claude Code Context

## Project Overview

HealthChain is an open-source Python framework for productionizing healthcare AI applications with native protocol understanding. It provides built-in FHIR support, real-time EHR connectivity, and production-ready deployment capabilities for AI/ML engineers working with healthcare systems.

**Key Problem Solved**: EHR data is specific, complex, and fragmented. HealthChain eliminates months of custom integration work by providing native understanding of healthcare protocols and data formats.

**Target Users**:
- HealthTech engineers building clinical workflow integrations
- LLM/GenAI developers aggregating multi-EHR data
- ML researchers deploying models as healthcare APIs

## Architecture & Structure

```
healthchain/
├── cli.py                 # Command-line interface
├── config/                # Configuration management
├── configs/               # YAML and Liquid templates
├── fhir/                  # FHIR resource utilities and helpers
├── gateway/               # API gateways (FHIR, CDS Hooks)
├── interop/               # Format conversion (FHIR ↔ CDA)
├── io/                    # Document and data I/O
├── models/                # Pydantic data models
├── pipeline/              # Pipeline components and NLP integrations
├── sandbox/               # Testing utilities with synthetic data
├── templates/             # Code generation templates
└── utils/                 # Shared utilities

tests/                     # Test suite
cookbook/                  # Usage examples and tutorials
docs/                      # MkDocs documentation
```

## Core Modules

### 1. Pipeline (`healthchain/pipeline/`)
- Build medical NLP pipelines with components like SpacyNLP
- Process clinical documents with automatic FHIR conversion
- Type-safe pipeline composition using generics

### 2. Gateway (`healthchain/gateway/`)
- **FHIRGateway**: Connect to multiple FHIR sources, aggregate patient data
- **CDSHooksGateway**: Real-time clinical decision support integration with Epic/Cerner
- **HealthChainAPI**: FastAPI-based application framework

### 3. FHIR Utilities (`healthchain/fhir/`)
- Type-safe FHIR resource creation and validation
- Bundle manipulation and resource extraction
- Recently refactored for clearer separation of concerns

### 4. Interop (`healthchain/interop/`)
- Convert between FHIR and CDA formats
- Configuration-driven templates using Liquid
- Support for various healthcare data standards

### 5. Sandbox (`healthchain/sandbox/`)
- Test CDS Hooks services with synthetic data
- Load from test datasets (Synthea, MIMIC)
- Request/response validation and debugging

### 6. I/O (`healthchain/io/`)
- Document processing and management
- Data loading for ML workflows
- Recently refactored for better organization

## Development Guidelines

### Code Style
- **Linter**: Ruff for code formatting and linting
- **Type Hints**: Use Pydantic models and type annotations throughout
- **Python Version**: Support 3.9-3.11 (not 3.12+)
- **Testing**: pytest with async support (`pytest-asyncio`)

### Key Dependencies
- **fhir.resources**: FHIR resource models (v8.0.0+)
- **FastAPI/Starlette**: API framework
- **Pydantic**: Data validation (v2.x, <2.11.0)
- **spaCy**: NLP processing (v3.x)
- **python-liquid**: Template engine for data conversion

### Patterns & Conventions

1. **Type Safety**: Leverage Pydantic models for all data structures
2. **Pipeline Pattern**: Use composable components with `Pipeline[T]` generic type
3. **Gateway Pattern**: Extend base gateway classes for new integrations
4. **Configuration**: Use YAML configs in `configs/` directory
5. **Templates**: Liquid templates for FHIR/CDA conversion

### Testing
- Tests organized in `tests/` mirroring source structure
- Use pytest fixtures for common test data
- Async tests for gateway/API functionality
- Recently consolidated test structure

### Documentation

**Style Guide:**
- **Concise**: Get to the point quickly - developers want answers, not essays
- **Friendly**: Conversational but professional tone; use emojis sparingly in headers
- **Developer-Friendly**: Code examples first, explanations second; show don't tell
- **Scannable**: Use bullets, tables, clear sections; respect developer's time
- **Practical**: Focus on "how" over "why"; include working code examples

**Good Documentation Examples:**
- `docs/index.md`: Clean feature overview, clear use case table, minimal prose
- `docs/quickstart.md`: Code-first approach, progressive complexity, practical examples
- `docs/cookbook/index.md`: Brief descriptions, clear outcomes, call-to-action

**Anti-Patterns (avoid):**
- Long paragraphs explaining concepts before showing code
- Over-explaining obvious functionality
- Academic or overly formal tone
- Excessive background before getting to the practical content

**Structure:**
- Lead with executable code examples
- Add brief context only where needed
- Use tables for feature comparisons
- Include links to full docs for deep dives
- Keep cookbook examples focused on one task

**Technical Details:**
- MkDocs with Material theme
- API reference auto-generated from docstrings using mkdocstrings
- Cookbook examples for common use cases
- Follow existing docs/ structure for consistency

## Recent Changes & Context

Based on recent commits:
- **FHIR Helper Module**: Refactored for clearer separation of utilities
- **I/O Module**: Refactored for better organization
- **Test Consolidation**: Tests reorganized for clarity
- **MIMIC Loader**: Added support for loading as dict for ML workflows
- **Bundle Conversion**: Config-based conversion instead of params

## Important Workflows

### Adding a New Gateway
1. Create class in `healthchain/gateway/` extending base gateway
2. Implement required protocol methods
3. Add configuration in `configs/`
4. Create sandbox test in `healthchain/sandbox/`
5. Add cookbook example in `cookbook/`

### Adding FHIR Resource Support
1. Use `fhir.resources` models
2. Add helper methods in `healthchain/fhir/` if needed
3. Update type hints and validation
4. Add tests with synthetic FHIR data

### Adding Data Conversion Templates
1. Create Liquid template in `configs/`
2. Add configuration YAML
3. Implement in `healthchain/interop/`
4. Test with real healthcare data examples

## Common Gotchas

1. **Pydantic v2**: Use v2 patterns, but stay <2.11.0 for compatibility
2. **NumPy**: Locked to <2.0.0 for spaCy compatibility
3. **FHIR Validation**: Always validate resources before serialization
4. **Async/Sync**: Gateway operations are async, pipeline operations are sync
5. **Healthcare Standards**: Follow HL7 FHIR R4 and CDS Hooks specifications

## Testing with Real Data

- **Synthea**: Synthetic patient generator for realistic test data
- **MIMIC**: Medical Information Mart for Intensive Care dataset support
- **Sandbox**: Use `SandboxClient` for end-to-end testing without real EHR

## Security & Compliance

- OAuth2 authentication support for FHIR endpoints
- Audit trails and data provenance (roadmap item)
- HIPAA compliance features (roadmap item)
- No PHI in tests - use synthetic data only

## Deployment

- Docker/Kubernetes support (enhanced support on roadmap)
- FastAPI apps with Uvicorn
- OpenAPI/Swagger documentation auto-generated
- Environment-based configuration

## Resources

- Documentation: https://dotimplement.github.io/HealthChain/
- Repository: https://github.com/dotimplement/HealthChain
- Discord: https://discord.gg/UQC6uAepUz
- Standards: HL7 FHIR R4, CDS Hooks
