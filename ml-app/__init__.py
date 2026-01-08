"""
ML Healthcare API Deployment Package

This package provides a production-ready template for deploying ML models
as Healthcare FHIR APIs with OAuth2 authentication.

Components:
    - app.py: Main FastAPI application with CDS Hooks and FHIR Gateway
    - auth.py: OAuth2 JWT Bearer authentication
    - config.py: Pydantic-based configuration management
    - train_demo_model.py: Demo model training script

Usage:
    # Train demo model (optional)
    python ml-app/train_demo_model.py

    # Run the API
    python ml-app/app.py

    # Or with uvicorn directly
    cd ml-app && uvicorn app:app --reload
"""

from .config import Settings, get_settings
from .auth import OAuth2JWTBearer, UserClaims, get_current_user

__all__ = [
    "Settings",
    "get_settings",
    "OAuth2JWTBearer",
    "UserClaims",
    "get_current_user"
]
