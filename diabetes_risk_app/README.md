# Diabetes Risk Monitoring System

A production-ready healthcare AI application built with HealthChain.

## Quick Start

1. **Train the model**:
   ```bash
   source venv/bin/activate
   cd models
   python train_model.py
   cd ..
   ```

2. **Start the application**:
   ```bash
   python app.py
   ```

3. **Test the application**:
   Visit http://localhost:8000/cds-services

4. **Run tests**:
   ```bash
   pytest tests/ -v
   ```

## Documentation

See the main guide: `../DIABETES_RISK_APP_GUIDE.md`

## Configuration

Edit `config/fhir_servers.yaml` to add your FHIR server credentials.
