> This template is meant to be a starting point; feel free to remove any sections that you can't really fill out just yet.
>
# RFC NNN: <Short, descriptive title>

- Author: <name or GitHub handle>
- Status: Draft | In Review | Accepted | Rejected | Superseded
- Created: <YYYY-MM-DD>
- Related Issue(s): #<issue-number>
- Related Discussion(s): <link(s) if any>

## 1. Summary

One or two paragraphs describing the problem and the proposed solution at a high level, focused on HealthChain’s goals and users.

## 2. Problem statement

- What problem are we trying to solve?
- Who is affected (e.g. API consumers, operators, patients, integrators)?
- Why is this important now?

Include any relevant context, such as existing limitations or incidents.

## 3. Goals and non-goals

### Goals

- Clear, concrete goals this RFC aims to achieve.

### Non-goals

- Things that are explicitly out of scope for this change to avoid scope creep.

## 4. Background and context

Summarize relevant existing behavior, architecture, and constraints in HealthChain.
Link to code, docs, or external standards (e.g. FHIR, SMART on FHIR, OIDC) that inform the design.

## 5. Proposed design

Describe the proposed solution in enough detail that another contributor could implement it:

- High-level architecture and data flow.
- Responsibilities of each component (e.g. Gateway, services, auth provider).
- API and contract changes (endpoints, request/response shapes, error handling).
- Configuration and operational considerations.

Diagrams are welcome but optional.

## 6. Alternatives considered

List alternative approaches that were considered and briefly explain why they were not chosen.
This helps future readers understand trade-offs and avoid rehashing old discussions.

## 7. Security, privacy, and compliance

Explain the impact on:

- Authentication and authorization behavior.
- Data confidentiality, integrity, and availability.
- Regulatory or standards alignment (e.g. healthcare-specific concerns if applicable).

Call out new risks and how they are mitigated.

## 8. Migration and rollout plan

- How will this be rolled out (flags, gradual rollout, big-bang)?
- How will existing deployments migrate, if applicable?
- How will rollback work if something goes wrong?

## 9. Testing and observability

- What tests are required (unit, integration, e2e)?
- Any new metrics, logs, or traces needed to operate this change?

## 10. Open questions

List any open questions that need to be answered before accepting the RFC, or things to be resolved during implementation.
