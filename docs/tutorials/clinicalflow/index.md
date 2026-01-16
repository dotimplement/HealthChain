# ClinicalFlow Tutorial

Build your first Clinical Decision Support (CDS) service with HealthChain.

## The Scenario

You're a HealthTech engineer at a hospital system. The clinical informatics team needs a CDS service that:

1. **Receives patient context** when a physician opens a chart
2. **Analyzes existing conditions and medications**
3. **Returns actionable alerts** for potential drug interactions or care gaps

By the end of this tutorial, you'll have a working CDS Hooks service that integrates with EHR systems like Epic.

## What You'll Build

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   EHR System    │─────>│  Your CDS       │─────>│  Clinical       │
│   (Epic, etc.)  │      │  Service        │      │  Alert Cards    │
└─────────────────┘      └─────────────────┘      └─────────────────┘
        │                        │
        │                        │
        ▼                        ▼
   Patient context          NLP Pipeline
   (FHIR resources)         (HealthChain)
```

## What You'll Learn

| Step | What You'll Learn |
|------|-------------------|
| [Setup](setup.md) | Install dependencies, create project structure |
| [FHIR Basics](fhir-basics.md) | Understand Patient, Condition, and Medication resources |
| [Build Pipeline](pipeline.md) | Create an NLP pipeline with Document containers |
| [Create Gateway](gateway.md) | Expose your pipeline as a CDS Hooks service |
| [Test with Sandbox](testing.md) | Validate with synthetic patient data |
| [Next Steps](next-steps.md) | Production deployment and extending your service |

## Prerequisites

- **Python 3.10+** installed
- **Basic Python knowledge** (functions, classes, imports)
- **REST API familiarity** (HTTP methods, JSON)
- Healthcare knowledge is helpful but not required

## Time Required

This tutorial takes approximately **45 minutes** to complete.

## Ready?

Let's start by [setting up your project](setup.md).
