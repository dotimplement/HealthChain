# Events

The FHIR Gateway emits events for all operations. The events are emitted using the `EventDispatcher`.

!!! warning "Develoment Use Only"
    This is a development feature and may change in future releases.



## Event System

The FHIR Gateway uses the `EventDispatcher` to emit events.

## Event Types

- `ehr.generic`
- `fhir.read`
- `fhir.search`
- `fhir.update`
- `fhir.delete`
- `fhir.create`
- `cds.patient.view`
- `cds.encounter.discharge`
- `cds.order.sign`
- `cds.order.select`
- `notereader.sign.note`
- `notereader.process.note`

## Automatic Events

The FHIR Gateway automatically emits events for all operations:

```python
from healthchain.gateway.events.dispatcher import local_handler

# Listen for FHIR read events
@local_handler.register(event_name="fhir.read")
async def audit_fhir_access(event):
    event_name, payload = event
    print(f"FHIR Read: {payload['resource_type']}/{payload['resource_id']} from {payload.get('source', 'unknown')}")

# Listen for patient-specific events
@local_handler.register(event_name="fhir.patient.*")
async def track_patient_access(event):
    event_name, payload = event
    operation = event_name.split('.')[-1]  # read, create, update, delete
    print(f"Patient {operation}: {payload['resource_id']}")
```

### Custom Event Creation

```python
# Configure custom event creation
def custom_event_creator(operation, resource_type, resource_id, resource=None, source=None):
    """Create custom events with additional metadata."""
    return EHREvent(
        event_type=EHREventType.FHIR_READ,
        source_system=source or "unknown",
        timestamp=datetime.now(),
        payload={
            "operation": operation,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "user_id": get_current_user_id(),  # Your auth system
            "session_id": get_session_id(),
            "ip_address": get_client_ip()
        },
        metadata={
            "compliance": "HIPAA",
            "audit_required": True
        }
    )

# Apply to gateway
gateway.events.set_event_creator(custom_event_creator)
```
