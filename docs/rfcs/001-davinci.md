## [RFC] Da Vinci Prior Authorization Profile Implementation (CRD/DTR/PAS)

### Context
CMS-0057-F mandates that payers implement Prior Authorization APIs using HL7 Da Vinci Implementation Guides (effective Jan 2027). HealthChain already provides the core intelligence layer (multi-source FHIR aggregation, AI/NLP enrichment, CDS Hooks orchestration), but lacks **Da Vinci-specific FHIR profile support** needed for EHR/payer interoperability.

This RFC proposes implementing typed FHIR profiles for Da Vinci CRD/DTR/PAS Implementation Guides, enabling HealthChain to serve as production middleware for prior authorization burden reduction use cases while leveraging existing AI/ML capabilities for clinical data extraction and medical necessity determination.

![CDS Hooks cards → DTR pre-population → PAS submission](./assets/pa-stack.png)

### Problem Statement

- **Problem**: Providers spend 13+ hours/week on prior authorization administrative burden. CMS-0057-F mandates payers expose Prior Authorization APIs using Da Vinci IGs, but HealthChain cannot currently produce conformant requests/responses.
​
- **Who is affected**:
    - **API integrators**: EHR vendors and middleware developers needing Da Vinci conformance
    - **Operators**: Healthcare organizations deploying HealthChain for PA automation
    - **Providers**: Clinicians who benefit from reduced administrative burden via AI-powered PA workflows

- **Why now**: CMS-0057-F compliance deadline (Jan 2027) creates market demand. Existing HealthChain AI capabilities (NLP extraction, clinical coding) are strong fit for PA automation, but lack profile-level conformance.


### Goals and non-goals

#### Goals
- Implement Da Vinci CRD/DTR/PAS FHIR profiles as typed Pydantic models with validation
- Add production security (OAuth 2.0/SMART, audit logging, error resilience)
- Create lightweight reference implementations and develop against Da Vinci IG Inferno test suites to validate conformance
- Create cookbook tutorials to demonstrate core pattern of integrating NLP/AI capabilities with production PA workflows
​
#### Non-goals
- Rebuilding existing components
- Native CQL engine or validator implementation (adapter to external engines only)
- SMART app UI/questionnaire rendering (middleware focused)
- X12 278 translation (only relevant to non-compliant payers post-deadline, external integration if needed)
- More general production deployment features will be addressed in a separate RFC


### Background and context

**Existing HealthChain capabilities:**

- **FHIRGateway**: Multi-source EHR data aggregation
- **CDSHooksService**: Generic CDS Hooks protocol support
- **HealthChainAPI**: Manage multiple endpoints in one unified API
- **NLP Pipeline**: Document handling focused (clinical coding, documentation extraction)
- **InteropEngine**: Convert legacy data into pipeline (CDA/HL7v2 pending)
- **SandboxClient**: Local testing of CDS hooks servers
- **Event-driven architecture**: Async processing, logging

**Da Vinci IGs for Prior Authorization:**

- **CRD (Coverage Requirements Discovery)**: CDS Hooks-based real-time payer guidance at order/appointment time
- **DTR (Documentation Templates and Rules)**: SMART app for questionnaire-based data collection with CQL-driven pre-population
- **PAS (Prior Authorization Support)**: FHIR API for submitting/tracking authorization requests via `$submit` operation

**Regulatory context:**
CMS-0057-F mandates payers implement Prior Authorization APIs using these IGs by Jan 2027 to reduce provider burden.

### Proposed design

The goal is to keep the implementation *lean*: build a lightweight layer around the existing Pydantic-based FHIR data validators, utilities, and service layers that achieves Da Vinci CRD/DTR/PAS Profile conformance.

Innovators should be able to build minimum viable CRD/DTR/PAS workflows leveraging HealthChain's AI/ML capabilities. Further requirements should arise from feedback and iteration from pilot users and design partners.

#### High-level architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    EHR / Provider System                    │
└─────────────────────┬───────────────────────────────────────┘
                      │ CDS Hooks / FHIR API
┌─────────────────────▼───────────────────────────────────────┐
│                  HealthChain Middleware                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Da Vinci Profile Layer (NEW)                        │   │
│  │  • CRD Card Builders (coverage-assertion-id, links)  │   │
│  │  • PAS Bundle Builders (Claim + supportingInfo)      │   │
│  │  • DTR/SDC Models (Questionnaire enrichment)         │   │
│  │  • US Core Validators                                │   │
│  └───────────────────┬──────────────────────────────────┘   │
│  ┌──────────────────▼───────────────────────────────────┐   │
│  │  Existing AI/ML Layer                                │   │
│  │  • NLP Pipeline: Clinical data extraction            │   │
│  │                  + document handling                 │   │
│  │  • InteropEngine: Legacy format conversion           │   │
│  │  • FHIRGateway: Multi-source data aggregation        │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────┬───────────────────────────────────────┘
                      │ FHIR + OAuth tokens
┌─────────────────────▼───────────────────────────────────────┐
│                   Payer APIs (CRD/PAS)                      │
└─────────────────────────────────────────────────────────────┘
```


### Da Vinci IG Requirements

| IG Component                       | Requirement                                                  | Current Status                                               | To Implement                                                 |
|------------------------------------|--------------------------------------------------------------|--------------------------------------------------------------|--------------------------------------------------------------|
| **US Core Profile**                | US Core IG STU 3.1.1, USCDI (v1/3/4) conformance             | Generic FHIR R4 support                                      | - Add helpers for setting `meta.profile` to US Core canonical URLs<br><br>- Add commonly required US Core search parameter constants/builders<br><br>- Add a profile validation helper that wraps an external validator service <br><br>- Add basic configuration management for core version/profile sets |
| **CRD - CDS Hooks Client**         | Provider should initiate request to payer CDS server         | `CDSHookService` creates CDS hook server and `SandboxClient` acts as a CDS client | Refactor CDS components in`SandboxClient` to a dedicated CDS Hooks client module |
| **CRD - CDS Hooks Data Models**    | [Support 6 hooks specified by Da Vinci CRD](https://build.fhir.org/ig/HL7/davinci-crd/branches/__default/en/hooks.html) | - Supports data models for`patient-view`, `encounter-discharge`<br><br>- Generic CDS response cards | - Add models for required hooks: `appointment-book`, `order-sign`, `order-dispatch`, `order-select`, `encounter-start`<br><br>- Add models for CRD-specific cards (`covereage-assertion-id`, links) |
| **CRD - OAuth2/SMART Client Flow** | Support SMART-on-FHIR OAuth client flows                     | Not implemented                                              | Implement SMART-on-FHIR OAuth client support (Integrate with Keycloak, obtain FHIR access tokens  for`fhirAuthorization`) |
| **DTR - dataRequirement parsing**  | Fetch FHIR resources from the EHR based on `Library` `dataRequirement` sections | Generic FHIR R4 resources support                            | Add helpers for parsing `dataRequirement` to FHIR queries and handling `Questionnaire` related resources |
| **DTR - CQL Execution**            | Execute CQL expressions for pre-population                   | Not implemented                                              | Add adapter / wrapper to external CQL engines (CQF Ruler, HAPI FHIR CQL) with FHIR data pass-through. |
| **PAS - Claims Bundle Builder**    | Construct PAS-conformant `Claim` bundles with `supportingInfo`, `DocumentReference` | Generic FHIR R4 resources support                            | Add helpers for building PAS-profiled `Claim`/`ClaimResponse`/`PASBundle` |


**Notes**:
- Full US Core Profile, typed SDC models etc. - develop incrementally on a use-case by use-case basis instead of all at once (advantage of open source community). Use the Inferno test suites for CRD/DTR/PAS to catch any must implement gaps.
- Implementation priority CRD > PAS > DTR, based on maturity of existing components (biggest gap is DTR requirements)
- Demonstrate the following patterns as reference implementations / cookbook examples:
  - Using `CDSHooksClient` to create a CRD client - show explicit patient search pattern for legacy EHRs that don’t support CDS Hooks (FHIRGateway sits in front of CDSClient)
  - Using `FHIRGateway` to create a DTR client (route EHR FHIR API and payer `/Questionnaire/$questionnaire-package` endpoints) with NLP capabilities for questionnaire pre-population
  - Using `FHIRGateway` to create a PAS client (route EHR FHIR API and payer `/Claim/$submit` endpoints) to pull documents from multiple sources, focusing on demontrating the `InteropEngine` and `DocumentReference` handling


**Ideas for future**:
- **Event-driven orchestration (FHIR subscription)**: 
  - **CRD - intermediary / ePA coordinator**: for EHRs without native CDS Hooks support - [there's capability for event listening and dispatching in HealthChain](https://dotimplement.github.io/HealthChain/reference/gateway/events/) , which could be integrated with FHIR subscription / EHR-related events (EHR events -> FHIRGateway -> CRD calls -> EHR notifications) (design partner needed?)
  - **PAS - response handling**: FHIR subscription or polling for status tracking (`$inquire`)



### Open Questions
1. **Timeline** - what can we work around?
2. **Priority order** - what profiles/features should be prioritized?


### Request for Feedback
Please review attached plan and discuss in next weekly sync. Focus areas:

- Architecture approach
- Milestone priorities and timeline
- Conformance testing strategy
- Input from industry partners?
- Any critical components missing?

---
### References
- [CMS-0057-F Fact Sheet](https://www.cms.gov/newsroom/fact-sheets/cms-interoperability-and-prior-authorization-final-rule-cms-0057-f)
- [Da Vinci CRD IG](https://www.hl7.org/fhir/us/davinci-crd/)
- [Da Vinci PAS IG](https://build.fhir.org/ig/HL7/davinci-pas/)
- [Da Vinci DTR IG](https://www.hl7.org/fhir/us/davinci-dtr/)


#### Implementation Guides
- [Da Vinci CRD IG v2.0.1 (STU)](https://build.fhir.org/ig/HL7/davinci-crd/)
- [Da Vinci DTR IG v2.0.0 (STU)](https://build.fhir.org/ig/HL7/davinci-dtr/)
- [Da Vinci PAS IG v2.0.1 (STU)](https://build.fhir.org/ig/HL7/davinci-pas/)

#### Reference Implementations
- [HL7-DaVinci GitHub Organization](https://github.com/HL7-DaVinci)
- [CRD Reference Implementation](https://github.com/HL7-DaVinci/CRD)
- [DTR Reference Implementation](https://github.com/HL7-DaVinci/dtr)
- [PAS Reference Implementation](https://github.com/HL7-DaVinci/prior-auth)
- [Test EHR (HAPI FHIR Server)](https://github.com/HL7-DaVinci/test-ehr)
- [CDS Library (Rules & Questionnaires)](https://github.com/HL7-DaVinci/CDS-Library)

#### Testing & Conformance
- [CRD Inferno Test Kit](https://fhir.healthit.gov/test-kits/davinci-crd/)
- [DTR Inferno Test Kit](https://github.com/inferno-framework/davinci-dtr-test-kit)
- [PAS Inferno Test Kit](https://inferno.healthit.gov/test-kits/davinci-pas/)

#### Supporting Standards
- [US Core IG v3.1.1 (STU)](https://www.hl7.org/fhir/us/core/STU3.1.1/)
- [SMART App Launch v1.0.0](https://www.hl7.org/fhir/smart-app-launch/1.0.0/)
- [USCDI v4](https://www.healthit.gov/uscdi)
