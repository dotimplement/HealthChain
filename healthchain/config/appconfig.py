"""
App-level configuration model for HealthChain projects.

Loads and validates healthchain.yaml from the project root.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from pydantic import BaseModel, field_validator

logger = logging.getLogger(__name__)

_CONFIG_FILENAME = "healthchain.yaml"


class SourceConfig(BaseModel):
    """A FHIR data source. Credentials are loaded from environment variables."""

    env_prefix: str  # e.g. "MEDPLUM" reads MEDPLUM_CLIENT_ID, MEDPLUM_BASE_URL etc.

    def to_fhir_auth_config(self):
        """Instantiate FHIRAuthConfig by reading env vars for this source's prefix."""
        from healthchain.gateway.clients.fhir.base import FHIRAuthConfig

        return FHIRAuthConfig.from_env(self.env_prefix)


class LLMConfig(BaseModel):
    """LLM provider settings. API key is read from the standard env var for each provider."""

    provider: str = "anthropic"  # anthropic | openai | google | huggingface
    model: str = "claude-opus-4-6"
    max_tokens: int = 512

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        allowed = {"anthropic", "openai", "google", "huggingface"}
        if v not in allowed:
            raise ValueError(f"provider must be one of: {', '.join(sorted(allowed))}")
        return v

    def to_langchain(self):
        """Instantiate the configured LangChain chat model."""
        if self.provider == "anthropic":
            from langchain_anthropic import ChatAnthropic

            return ChatAnthropic(model=self.model, max_tokens=self.max_tokens)
        elif self.provider == "openai":
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(model=self.model, max_tokens=self.max_tokens)
        elif self.provider == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI

            return ChatGoogleGenerativeAI(
                model=self.model, max_output_tokens=self.max_tokens
            )
        elif self.provider == "huggingface":
            from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

            llm = HuggingFaceEndpoint(repo_id=self.model, max_new_tokens=self.max_tokens)
            return ChatHuggingFace(llm=llm)


class ServiceConfig(BaseModel):
    type: str = "cds-hooks"
    port: int = 8000


class DataConfig(BaseModel):
    patients_dir: str = "./data"
    output_dir: str = "./output"


class TLSConfig(BaseModel):
    enabled: bool = False
    cert_path: str = "./certs/server.crt"
    key_path: str = "./certs/server.key"


class SecurityConfig(BaseModel):
    auth: str = "none"
    tls: TLSConfig = TLSConfig()
    allowed_origins: List[str] = ["*"]

    @field_validator("auth")
    @classmethod
    def validate_auth(cls, v: str) -> str:
        allowed = {"none", "api-key", "smart-on-fhir"}
        if v not in allowed:
            raise ValueError(f"auth must be one of: {', '.join(sorted(allowed))}")
        return v

class AuditConfig(BaseModel):
    enabled: bool = False
    database_url: Optional[str] = None # To store user's info
    retention_days: int = 2190
    personal_identifier_info : bool = False
    audit_log: str = "./logs/audit.jsonl"

    @field_validator("retention_days")
    @classmethod
    def validate_retention(cls,v:int) -> int:
        if v < 2190:
            raise ValueError("retention days must meet six-year HIPAA retention period.")
        return v

class ComplianceConfig(BaseModel):
    hipaa: bool = False
    audit : AuditConfig = AuditConfig()

    def model_post_init(self,__context) -> None:
        if self.hipaa and not self.audit.enabled:
            self.audit = AuditConfig(
                enabled = True,
                database_url = self.audit.database_url,
                retention_days = self.audit.retention_days,
                personal_identifier_info = self.audit.personal_identifier_info,
                audit_log = self.audit.audit_log
            )



class EvalConfig(BaseModel):
    enabled: bool = False
    provider: str = "mlflow"
    tracking_uri: str = "./mlruns"
    track: List[str] = ["model_inference", "cds_card_returned", "card_feedback"]


class SiteConfig(BaseModel):
    name: str = ""
    environment: str = "development"

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(
                f"environment must be one of: {', '.join(sorted(allowed))}"
            )
        return v


class AppConfig(BaseModel):
    name: str = "my-healthchain-app"
    version: str = "1.0.0"
    service: ServiceConfig = ServiceConfig()
    data: DataConfig = DataConfig()
    security: SecurityConfig = SecurityConfig()
    compliance: ComplianceConfig = ComplianceConfig()
    eval: EvalConfig = EvalConfig()
    site: SiteConfig = SiteConfig()
    sources: Dict[str, SourceConfig] = {}
    llm: Optional[LLMConfig] = None

    @classmethod
    def from_yaml(cls, path: Path) -> "AppConfig":
        """Load AppConfig from a YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return cls(**data)

    @classmethod
    def load(cls) -> Optional["AppConfig"]:
        """Load healthchain.yaml from the current working directory if it exists."""
        config_path = Path(_CONFIG_FILENAME)
        if config_path.exists():
            try:
                return cls.from_yaml(config_path)
            except Exception as e:
                logger.warning(f"Failed to load {_CONFIG_FILENAME}: {e}")
        return None
