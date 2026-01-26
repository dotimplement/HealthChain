# Next Steps

You've built a working CDS service. Here's how to take it further.

## What You've Accomplished

In this tutorial, you:

- Set up a HealthChain development environment
- Learned FHIR basics (Patient, Condition, MedicationStatement)
- Built an NLP pipeline with Document containers
- Created a CDS Hooks gateway service
- Tested with the sandbox and synthetic data


## What to Do Next

### Improve the NLP

The NLP was hard coded in our example but HealthChain has simple pipeline integrations for spacy, huggingface and Langchain. Try to replace keyword matching with trained models.


### Add FHIR Output

Convert extracted entities to FHIR resources:

```python
from healthchain.pipeline.components import FHIRProblemListExtractor

pipeline.add_node(FHIRProblemListExtractor())

# Now doc.fhir.problem_list contains FHIR Condition resources
```

## Learn More

Explore HealthChain's [cookbook](../../../cookbook/index.md) documentation, we have a variety of cookbooks that will let you build upon the basics from this tutorial.


## Congratulations!

You've completed the ClinicalFlow tutorial. You now have the foundation to build production-ready healthcare AI applications with HealthChain.
