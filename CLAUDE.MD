# HealthChain - Claude Code Context

> **Purpose**: This file guides AI assistants and developers working on HealthChain. It encodes coding standards, constraints, and workflows to keep architecture and domain judgment in human hands. It's a working document that will be updated as the project evolves.

## 0. Project Overview

HealthChain is an open-source Python framework for productionizing healthcare AI applications with native protocol understanding. It provides built-in FHIR support, real-time EHR connectivity, and deployment tooling for healthcare AI/ML systems.

**Key Problem**: EHR data is specific, complex, and fragmented. HealthChain eliminates months of custom integration work by understanding healthcare protocols and data formats out of the box.

**Target Users**:
- HealthTech engineers building clinical workflow integrations
- LLM/GenAI developers aggregating multi-EHR data
- ML researchers deploying models as healthcare APIs

For more background, see @README.md and @docs/index.md.

---

## 1. Non-Negotiable Golden Rules

| # | AI *may* do | AI *must NOT* do |
|---|-------------|------------------|
| G-0 | When unsure about implementation details or requirements, ask developer for clarification before making changes. | ❌ Write changes or use tools when you are not sure about something project specific, or if you don't have context for a particular feature/decision. |
| G-1 | Generate code inside `healthchain/` or explicitly pointed files. | ❌ Modify or create test files without explicit approval. |
| G-2 | For changes >200 LOC or >3 files, propose a plan and wait for confirmation. | ❌ Refactor large modules without human guidance. |
| G-3 | Follow lint/style configs (`pyproject.toml`, `.ruff.toml`). Use `ruff` for formatting. | ❌ Reformat code to any other style. |
| G-4 | Stay within the current task context. Inform the dev if it'd be better to start afresh. | ❌ Continue work from a prior prompt after "new task" – start a fresh session. |

---

## 2. Testing Discipline

| What | AI CAN Do | AI MUST NOT Do |
|------|-----------|----------------|
| Implementation | Generate business logic | Write new tests without confirmation |
| Test Planning | Suggest test scenarios and coverage gaps | Implement test code during design phase |
| Debugging | Analyze test failures and suggest fixes | Modify test expectations without approval |

**Key principle**: Tests encode business requirements and human intent. AI assistance is welcome for suggestions, maintenance, and execution, but new test creation always requires explicit confirmation.

---

## 3. Build, Test & Utility Commands

Use `uv` for all development tasks:

```bash
# Testing
uv run pytest

# Linting & Formatting
uv run ruff check . --fix              # Lint and auto-fix
uv run ruff format .                   # Format code

# Dependency Management
uv sync                                # Install/sync dependencies
uv add <package>                       # Add dependency
uv add --dev <package>                 # Add dev dependency
```

---

## 4. Coding Standards

- **Python**: 3.10-3.11, prefer sync for legacy EHR compatibility; async available for modern systems but use only when explicitly needed
- **Dependencies**: Pydantic v2 (<2.11.0), NumPy <2.0.0 (spaCy compatibility)
- **Environment**: Use `uv` to manage dependencies and run commands (`uv run <command>`)
- **Formatting**: `ruff` enforces project style
- **Typing**: Always use explicit type hints, even for obvious types; Pydantic v2 models for external data
- **Naming**:
  - Code: `snake_case` (functions/vars), `PascalCase` (classes), `SCREAMING_SNAKE` (constants)
  - Files: No underscores, e.g., `fhiradapter.py` not `fhir_adapter.py`
- **Error Handling**: Prefer specific exceptions over generic
- **Documentation**: Docstrings for public APIs only
- **Healthcare Standards**: Follow HL7 FHIR and CDS Hooks specifications
- **Testing**: Separate test files matching source file patterns. Use flat functions instead of classes for tests.

---

## 5. Project Layout & Core Components

```
healthchain/
├── cli.py        # CLI entrypoint
├── config/       # Configuration management
├── configs/      # YAML + Liquid configs/templates
├── fhir/         # FHIR utilities and helpers
├── gateway/      # API gateways (FHIR, CDS Hooks)
├── interop/      # Format conversion (FHIR ↔ CDA, etc.)
├── io/           # Data containers, adapters, mappers (external formats ↔ HealthChain)
├── models/       # Pydantic data models
├── pipeline/     # Pipeline components and NLP integrations
├── sandbox/      # CDS Hooks testing scenarios & data loaders
├── templates/    # Code generation templates
└── utils/        # Shared utilities

tests/            # Test suite
cookbook/         # Usage examples and tutorials
docs/             # MkDocs documentation
```

### Key Modules (When to Use What)

| Module | Purpose |
|--------|---------|
| `pipeline/` | Document/patient NLP with `Pipeline[T]` generics |
| `gateway/` | EHR connectivity and protocol handling (CDS Hooks, FHIR APIs, SOAP/CDA) |
| `fhir/` | FHIR resource utilities (fhir.resources models) and helpers |
| `interop/` | Format conversion with Liquid templates + YAML (FHIR ↔ CDA, etc.) |
| `io/` | **Containers**: FHIR+AI native structures<br>**Mappers**: semantic mapping (ML features, OMOP)<br>**Adapters**: interface with external formats (CDA, CSV) |
| `sandbox/` | Testing client for healthcare services (CDS Hooks, SOAP) & dataset loaders for common test datasets (MIMIC-IV on FHIR, Synthea, etc.) |

### Key File References

**FHIR Utilities Pattern**: @healthchain/fhir/
**Adapter Pattern**: @healthchain/io/adapters/
**Container Pattern**: @healthchain/io/containers/
**Mapper Pattern**: @healthchain/io/mappers/
**Pipeline Pattern**: @healthchain/pipeline/
**Gateway Pattern**: @healthchain/gateway/

---

## 6. Common Workflows

### AI Assistant Workflow

When responding to user instructions, follow this process:

1. **Consult Relevant Guidance**: Review this CLAUDE.md and relevant patterns in @healthchain/ for the request. Look up relevant files, information, best practices, etc. using the internet or tools if necessary.
2. **Clarify Ambiguities**: If anything is unclear, ask targeted questions before proceeding. Don't make assumptions about business logic or domain requirements.
3. **Break Down & Plan**:
   - Break down, think through the problem, and create a rough plan
   - Reference project conventions and best practices
   - **Trivial tasks**: Start immediately
   - **Non-trivial tasks** (>200 LOC or >3 files): Present plan → wait for user confirmation
4. **Execute**:
   - Make small, focused diffs
   - Prefer existing abstractions over new ones
   - Run: `uv run ruff check . --fix && uv run ruff format .`
   - If stuck, return to step 3 to re-plan
5. **Review**: Summarize files changed, key design decisions, and any follow-ups or TODOs
6. **Session Boundaries**: If request isn't related to current context, suggest starting fresh to avoid confusion

### Adding New FHIR Resource Utilities

1. Check for existing utilities in @healthchain/fhir/
2. If missing, ask: "Create utility function for [ResourceType]?"
3. Follow pattern: MINIMUM VIABLE resource, all variable data as parameters
4. Avoid overly specific utilities; prefer generic
---

## 7. Common Pitfalls

**Do:**
- Use `uv run` to run commands instead of directly running files in the environment

**Don't:**
- Commit secrets (use environment variables or `.env` file)
- Make drive-by refactors
- Write code before planning
- Write tests during design phase

---

**Last updated**: 2025-12-17
