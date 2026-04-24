"""
App-level configuration model for HealthChain projects.

Loads and validates healthchain.yaml from the project root.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger(__name__)

_CONFIG_FILENAME = "healthchain.yaml"


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
    tls: TLSConfig = Field(default_factory=TLSConfig)
    allowed_origins: List[str] = Field(default_factory=lambda: ["*"])

    @field_validator("auth")
    @classmethod
    def validate_auth(cls, v: str) -> str:
        allowed = {"none", "api-key", "smart-on-fhir"}
        if v not in allowed:
            raise ValueError(f"auth must be one of: {', '.join(sorted(allowed))}")
        return v


class ComplianceConfig(BaseModel):
    hipaa: bool = False
    audit_log: str = "./logs/audit.jsonl"


class EvalConfig(BaseModel):
    enabled: bool = False
    provider: str = "mlflow"
    tracking_uri: str = "./mlruns"
    track: List[str] = Field(
        default_factory=lambda: [
            "model_inference",
            "cds_card_returned",
            "card_feedback",
        ]
    )


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


class ApplicationSettings(BaseModel):
    name: str
    version: str
    environment: str
    site_name: str = ""


class RuntimeSettings(BaseModel):
    service_type: str
    port: int
    auth: str
    tls_enabled: bool
    allowed_origins: List[str] = Field(default_factory=list)


class IntegrationSettings(BaseModel):
    patients_dir: str
    output_dir: str
    eval_enabled: bool
    eval_provider: str


class StartupValidationSummary(BaseModel):
    status: str
    config_path: Optional[str] = None
    application: ApplicationSettings
    runtime: RuntimeSettings
    integrations: IntegrationSettings
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class AppConfig(BaseModel):
    name: str = "my-healthchain-app"
    version: str = "1.0.0"
    service: ServiceConfig = Field(default_factory=ServiceConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    compliance: ComplianceConfig = Field(default_factory=ComplianceConfig)
    eval: EvalConfig = Field(default_factory=EvalConfig)
    site: SiteConfig = Field(default_factory=SiteConfig)

    @model_validator(mode="after")
    def validate_runtime_contract(self) -> "AppConfig":
        if self.security.tls.enabled and (
            not self.security.tls.cert_path or not self.security.tls.key_path
        ):
            raise ValueError(
                "security.tls requires both cert_path and key_path when tls.enabled is true"
            )
        return self

    @property
    def application_settings(self) -> ApplicationSettings:
        return ApplicationSettings(
            name=self.name,
            version=self.version,
            environment=self.site.environment,
            site_name=self.site.name,
        )

    @property
    def runtime_settings(self) -> RuntimeSettings:
        return RuntimeSettings(
            service_type=self.service.type,
            port=self.service.port,
            auth=self.security.auth,
            tls_enabled=self.security.tls.enabled,
            allowed_origins=list(self.security.allowed_origins),
        )

    @property
    def integration_settings(self) -> IntegrationSettings:
        return IntegrationSettings(
            patients_dir=self.data.patients_dir,
            output_dir=self.data.output_dir,
            eval_enabled=self.eval.enabled,
            eval_provider=self.eval.provider,
        )

    def build_startup_validation_summary(
        self,
        config_path: Optional[Path] = None,
        *,
        status: str = "valid",
        warnings: Optional[List[str]] = None,
        errors: Optional[List[str]] = None,
    ) -> StartupValidationSummary:
        return StartupValidationSummary(
            status=status,
            config_path=str(config_path) if config_path else None,
            application=self.application_settings,
            runtime=self.runtime_settings,
            integrations=self.integration_settings,
            warnings=warnings or [],
            errors=errors or [],
        )

    @classmethod
    def from_yaml(cls, path: Path) -> "AppConfig":
        """Load AppConfig from a YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return cls(**data)

    @classmethod
    def load_with_summary(
        cls, path: Optional[Path] = None, *, strict: bool = False
    ) -> tuple[Optional["AppConfig"], StartupValidationSummary]:
        config_path = path or Path(_CONFIG_FILENAME)
        if not config_path.exists():
            default_config = cls()
            summary = default_config.build_startup_validation_summary(
                config_path,
                status="defaulted",
                warnings=[
                    f"{config_path.name} not found; runtime will use HealthChain defaults."
                ],
            )
            return None, summary

        try:
            config = cls.from_yaml(config_path)
        except Exception as exc:
            message = f"Failed to load {config_path.name}: {exc}"
            summary = cls().build_startup_validation_summary(
                config_path,
                status="invalid",
                errors=[message],
            )
            if strict:
                raise ValueError(message) from exc
            logger.warning(message)
            return None, summary

        return config, config.build_startup_validation_summary(config_path)

    @classmethod
    def load(cls, *, strict: bool = False) -> Optional["AppConfig"]:
        """Load healthchain.yaml from the current working directory if it exists."""
        config, _summary = cls.load_with_summary(strict=strict)
        return config
