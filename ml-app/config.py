"""
Configuration and Settings Module

Manages application settings with environment variable support and validation.
Uses Pydantic Settings for type-safe configuration management.
"""

from functools import lru_cache
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Configuration
    api_title: str = Field(default="ML Healthcare API", description="API title")
    api_version: str = Field(default="1.0.0", description="API version")
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    debug: bool = Field(default=False, description="Enable debug mode")

    # OAuth2 Configuration (for incoming request authentication)
    oauth2_enabled: bool = Field(
        default=False,
        description="Enable OAuth2 JWT authentication for incoming requests"
    )
    oauth2_issuer: Optional[str] = Field(
        default=None,
        description="OAuth2 token issuer URL"
    )
    oauth2_audience: Optional[str] = Field(
        default=None,
        description="Expected audience claim in JWT"
    )
    oauth2_jwks_uri: Optional[str] = Field(
        default=None,
        description="JWKS endpoint for public key retrieval"
    )
    oauth2_algorithms: str = Field(
        default="RS256",
        description="Comma-separated list of allowed JWT algorithms"
    )

    # FHIR Server Configuration (Medplum)
    medplum_client_id: Optional[str] = Field(default=None)
    medplum_client_secret: Optional[str] = Field(default=None)
    medplum_base_url: Optional[str] = Field(default=None)
    medplum_token_url: Optional[str] = Field(default=None)

    # FHIR Server Configuration (Epic)
    epic_client_id: Optional[str] = Field(default=None)
    epic_client_secret: Optional[str] = Field(default=None)
    epic_client_secret_path: Optional[str] = Field(default=None)
    epic_base_url: Optional[str] = Field(default=None)
    epic_token_url: Optional[str] = Field(default=None)
    epic_key_id: Optional[str] = Field(default=None)

    # FHIR Server Configuration (Cerner)
    cerner_client_id: Optional[str] = Field(default=None)
    cerner_client_secret: Optional[str] = Field(default=None)
    cerner_base_url: Optional[str] = Field(default=None)
    cerner_token_url: Optional[str] = Field(default=None)

    # ML Model Configuration
    model_path: Optional[str] = Field(
        default=None,
        description="Path to trained model file"
    )
    schema_path: Optional[str] = Field(
        default=None,
        description="Path to feature schema YAML"
    )

    # Risk Thresholds
    high_risk_threshold: float = Field(
        default=0.7,
        description="Threshold for high risk classification"
    )
    moderate_risk_threshold: float = Field(
        default=0.4,
        description="Threshold for moderate risk classification"
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    @property
    def algorithms_list(self) -> list:
        """Parse algorithms string into list."""
        return [a.strip() for a in self.oauth2_algorithms.split(",")]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"
    }


class FHIRSourceConfig(BaseSettings):
    """Configuration for a single FHIR source."""
    client_id: str
    client_secret: Optional[str] = None
    client_secret_path: Optional[str] = None
    base_url: str
    token_url: str
    scope: str = "system/*.read system/*.write"
    use_jwt_assertion: bool = False
    key_id: Optional[str] = None

    def to_connection_string(self) -> str:
        """Generate FHIR connection string."""
        parts = [f"fhir://{self.base_url.replace('https://', '').replace('http://', '')}"]
        params = [f"client_id={self.client_id}"]

        if self.client_secret:
            params.append(f"client_secret={self.client_secret}")
        if self.token_url:
            params.append(f"token_url={self.token_url}")
        if self.scope:
            params.append(f"scope={self.scope}")

        if params:
            parts.append("?" + "&".join(params))

        return "".join(parts)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def get_oauth2_config(settings: Settings) -> dict:
    """Extract OAuth2 configuration as dictionary."""
    return {
        "enabled": settings.oauth2_enabled,
        "issuer": settings.oauth2_issuer,
        "audience": settings.oauth2_audience,
        "jwks_uri": settings.oauth2_jwks_uri,
        "algorithms": settings.algorithms_list
    }
