# Next Steps

You've built a working CDS service. Here's how to take it further.

## What You've Accomplished

In this tutorial, you:

- Set up a HealthChain development environment
- Learned FHIR basics (Patient, Condition, MedicationStatement)
- Built an NLP pipeline with Document containers
- Created a CDS Hooks gateway service
- Tested with the sandbox and synthetic data

## Production Considerations

### Authentication

Real EHR integrations require OAuth2 authentication:

```python
from healthchain.gateway import HealthChainAPI

app = HealthChainAPI(
    title="ClinicalFlow CDS Service",
    auth_config={
        "type": "oauth2",
        "token_url": "https://your-auth-server/token",
        "scopes": ["patient/*.read", "user/*.read"]
    }
)
```

### HTTPS

Always use HTTPS in production. With uvicorn:

```bash
uvicorn app:app --host 0.0.0.0 --port 443 --ssl-keyfile key.pem --ssl-certfile cert.pem
```

### Logging and Monitoring

Add structured logging:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("clinicalflow")

@app.cds_hooks(id="patient-alerts", ...)
def patient_alerts(context, prefetch):
    logger.info(f"Processing request for patient {context.get('patientId')}")
    # ... your logic
```

## Connect to Real EHR Sandboxes

### Epic Sandbox

1. Register at [Epic's Developer Portal](https://fhir.epic.com/)
2. Create an application
3. Configure your service URL
4. Test against Epic's sandbox environment

### Cerner Sandbox

1. Register at [Cerner's Developer Portal](https://code.cerner.com/)
2. Follow their CDS Hooks integration guide
3. Test with their Millennium sandbox

## Extend Your Service

### Add More Hooks

Support multiple trigger points:

```python
@app.cds_hooks(
    id="order-check",
    title="Medication Order Check",
    hook="order-select"
)
def check_medication_orders(context, prefetch):
    """Check for drug interactions when orders are selected."""
    # ... drug interaction logic
    pass


@app.cds_hooks(
    id="discharge-summary",
    title="Discharge Summary Generator",
    hook="encounter-discharge"
)
def generate_discharge_summary(context, prefetch):
    """Generate discharge summary at end of encounter."""
    # ... summarization logic
    pass
```

### Improve NLP

Replace keyword matching with trained models:

```python
from healthchain.pipeline.components.integrations import SpacyNLP

# Use a clinical NLP model
pipeline.add_node(SpacyNLP.from_model_id("en_core_sci_lg"))

# Or integrate with external services
from healthchain.pipeline.components import LLMComponent

pipeline.add_node(LLMComponent(
    provider="openai",
    model="gpt-4",
    prompt_template="Extract clinical conditions from: {text}"
))
```

### Add FHIR Output

Convert extracted entities to FHIR resources:

```python
from healthchain.pipeline.components import FHIRProblemListExtractor

pipeline.add_node(FHIRProblemListExtractor())

# Now doc.fhir.problem_list contains FHIR Condition resources
```

## Learn More

Explore HealthChain's documentation:

| Topic | Description |
|-------|-------------|
| [Gateway Reference](../../reference/gateway/gateway.md) | Deep dive into gateway patterns |
| [Pipeline Reference](../../reference/pipeline/pipeline.md) | Advanced pipeline configuration |
| [CDS Hooks Cookbook](../../cookbook/discharge_summarizer.md) | Complete CDS Hooks example |
| [Multi-EHR Integration](../../cookbook/multi_ehr_aggregation.md) | Connect to multiple EHRs |

## Get Help

- **Discord**: [Join our community](https://discord.gg/UQC6uAepUz)
- **GitHub**: [Report issues](https://github.com/dotimplement/healthchain/issues)
- **Office Hours**: Thursdays 4:30-5:30pm GMT

## Congratulations!

You've completed the ClinicalFlow tutorial. You now have the foundation to build production-ready healthcare AI applications with HealthChain.
