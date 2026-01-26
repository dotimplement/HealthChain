# ClinicalFlow Tutorial

Build your first Clinical Decision Support (CDS) service with HealthChain.

## The Scenario

You're a HealthTech engineer at a hospital. The clinical informatics team needs a service that:

1. **Receives patient context** when a physician opens a chart
2. **Analyzes existing conditions and medications**
3. **Returns actionable alerts** for potential drug interactions or care gaps

Doing this in practice has a number of pain points:

- **Complex protocol requirements** - CDS Hooks and FHIR have strict specifications that take weeks to implement correctly
- **Fragmented EHR data** - Patient information comes in different formats across systems, requiring custom parsing logic
- **No easy testing path** - Validating your service against realistic clinical scenarios typically requires access to live EHR systems
- **Integration boilerplate** - Writing the HTTP endpoints, request validation, and response formatting is repetitive but error-prone

HealthChain handles all of this for you, so you can focus on the clinical logic that matters.

By the end of this tutorial, you'll have a working CDS Hooks service that integrates with EHR systems like Epic.

## What You'll Build

We'll build a Pipeline that processes clinical text from an EHR and a Service that wraps around it to return Clinical Alert Cards.

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

Throughout this tutorial, we'll use the same sample patient - **John Smith** with hypertension and diabetes - so you can see how data flows from FHIR resources through your pipeline to clinical alerts.

## What You'll Learn

| Step | What You'll Learn |
|------|-------------------|
| [Setup](setup.md) | Install dependencies, create project structure |
| [FHIR Basics](fhir-basics.md) | Understand FHIR resources and how they flow into CDS Hooks requests |
| [Build Pipeline](pipeline.md) | Create an NLP pipeline that extracts conditions from clinical text |
| [Create Gateway](gateway.md) | Expose your pipeline as a CDS Hooks service that EHRs can call |
| [Test with Sandbox](testing.md) | Validate with sample patient data (simulating what Epic would send) |
| [Next Steps](next-steps.md) | Production deployment and extending your service |

## Prerequisites

- **Python 3.10+** installed
- **Basic Python knowledge** (functions, classes, imports)
- **REST API familiarity** (HTTP methods, JSON)
- Healthcare knowledge is helpful but not required

## Time Required

This tutorial takes approximately **30 minutes** to complete.

## Ready?

Let's start by [setting up your project](setup.md).
