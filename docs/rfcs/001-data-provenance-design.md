# RFC 001: Data Provenance Tracking Design (#166)

- Status: Resolved
- Related Issue(s): #166 (Data provenance tracking design)

---

## 1. Summary

HealthChain had basic data provenance tracking - resources could be tagged with their origin system and processing history
via `meta.source` and `meta.tag` - but nothing recorded that the tagging happened. 
Issue #166 addressed this by adding `create_provenance_audit_event()`, which creates a FHIR `AuditEvent` and 
emits a structured log entry each time provenance metadata is applied.

---

## 2. Original State of the Project

**`add_provenance_metadata(resource, source, tag_code, tag_display)`** in `healthchain/fhir/resourcehelpers.py` annotated a FHIR resource with:

- `meta.source` - set to `urn:healthchain:source:{source}` (e.g. `urn:healthchain:source:epic`)
- `meta.lastUpdated` - set to the current UTC timestamp
- `meta.tag` - optionally adds a processing tag (e.g. `aggregated`, `deduplicated`, `cdi`)

### What Was Missing

The existing system answered *"Where did this data come from?"* but not:
- *"When was this provenance tag applied?"*
- *"What system applied it?"*
- *"Is there any record of this event?"*

Provenance metadata travels with the resource and can be stripped or overwritten. There was no separate record that a provenance tagging event had occurred.


*Before the fix: provenance metadata is applied correctly, but no AuditEvent is created and the tagging goes unrecorded.*

---

## 3. The Fix

A new function `create_provenance_audit_event()` was added to `healthchain/fhir/resourcehelpers.py` and called inside `add_provenance_metadata()`. It creates a FHIR `AuditEvent` object capturing:

- **What** - the resource type and ID that was tagged
- **Where from** - the source system (e.g. `"epic"`)
- **When** - UTC timestamp at time of tagging
- **Tag applied** - the tag code included in the entity description


*After the fix: a structured PROVENANCE AUDIT log entry is emitted on every call to `add_provenance_metadata()`, confirming the event was recorded.*

Provenance tagging is no longer silent.

---

## 4. Bug Fix

`action="C"` was hardcoded in `create_provenance_audit_event()`. Since provenance tagging modifies an existing resource rather than creating a new one, the correct FHIR action code is `"U"` (Update). This was corrected.

---

## 5. Testing

Three tests cover the implementation in `tests/fhir/test_helpers.py`:

- `test_create_provenance_audit_event_returns_audit_event` - verifies the function returns a valid FHIR `AuditEvent` with correct fields (resource type, source, timestamp, tag code, action `"U"`)
- `test_create_provenance_audit_event_without_tag` - verifies the function works when no tag code is provided
- `test_add_provenance_metadata_calls_create_provenance_audit_event` - verifies `add_provenance_metadata()` calls `create_provenance_audit_event()` on every invocation
