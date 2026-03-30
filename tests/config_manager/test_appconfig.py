"""Tests for AppConfig — app-level configuration loaded from healthchain.yaml."""

import pytest

from healthchain.config.appconfig import AppConfig, LLMConfig


def test_appconfig_loads_valid_yaml(tmp_path):
    """AppConfig.from_yaml parses a valid healthchain.yaml correctly."""
    config_file = tmp_path / "healthchain.yaml"
    config_file.write_text(
        """
name: my-app
version: "2.0.0"
service:
  type: fhir-gateway
  port: 9000
site:
  environment: production
  name: Test Hospital
"""
    )
    config = AppConfig.from_yaml(config_file)

    assert config.name == "my-app"
    assert config.version == "2.0.0"
    assert config.service.type == "fhir-gateway"
    assert config.service.port == 9000
    assert config.site.environment == "production"
    assert config.site.name == "Test Hospital"


def test_appconfig_missing_fields_use_defaults(tmp_path):
    """AppConfig.from_yaml fills in defaults for any omitted fields."""
    config_file = tmp_path / "healthchain.yaml"
    config_file.write_text("name: minimal-app\n")

    config = AppConfig.from_yaml(config_file)

    assert config.name == "minimal-app"
    assert config.service.port == 8000
    assert config.service.type == "cds-hooks"
    assert config.security.auth == "none"
    assert config.security.tls.enabled is False
    assert config.compliance.hipaa is False
    assert config.eval.enabled is False
    assert config.site.environment == "development"


def test_appconfig_invalid_auth_raises(tmp_path):
    """AppConfig raises ValueError for unrecognised auth method."""
    config_file = tmp_path / "healthchain.yaml"
    config_file.write_text("security:\n  auth: magic-token\n")

    with pytest.raises(Exception):
        AppConfig.from_yaml(config_file)


def test_appconfig_invalid_environment_raises(tmp_path):
    """AppConfig raises ValueError for unrecognised environment value."""
    config_file = tmp_path / "healthchain.yaml"
    config_file.write_text("site:\n  environment: staging-uat\n")

    with pytest.raises(Exception):
        AppConfig.from_yaml(config_file)


def test_appconfig_load_returns_none_when_no_file(tmp_path, monkeypatch):
    """AppConfig.load returns None when healthchain.yaml is not present."""
    monkeypatch.chdir(tmp_path)
    assert AppConfig.load() is None


def test_appconfig_load_returns_config_when_file_present(tmp_path, monkeypatch):
    """AppConfig.load reads healthchain.yaml from the current directory."""
    (tmp_path / "healthchain.yaml").write_text("name: loaded-app\n")
    monkeypatch.chdir(tmp_path)

    config = AppConfig.load()

    assert config is not None
    assert config.name == "loaded-app"


def test_appconfig_load_returns_none_on_parse_error(tmp_path, monkeypatch):
    """AppConfig.load returns None and logs a warning when the file is malformed."""
    (tmp_path / "healthchain.yaml").write_text("security:\n  auth: bad-value\n")
    monkeypatch.chdir(tmp_path)

    # Should not raise — returns None gracefully
    result = AppConfig.load()
    assert result is None


def test_appconfig_tls_config_parsed(tmp_path):
    """AppConfig parses nested TLS config correctly."""
    config_file = tmp_path / "healthchain.yaml"
    config_file.write_text(
        """
security:
  tls:
    enabled: true
    cert_path: ./certs/cert.pem
    key_path: ./certs/key.pem
"""
    )
    config = AppConfig.from_yaml(config_file)

    assert config.security.tls.enabled is True
    assert config.security.tls.cert_path == "./certs/cert.pem"
    assert config.security.tls.key_path == "./certs/key.pem"


def test_llmconfig_valid_providers():
    """LLMConfig accepts all supported providers."""
    for provider in ("anthropic", "openai", "google", "huggingface"):
        config = LLMConfig(provider=provider)
        assert config.provider == provider


def test_llmconfig_invalid_provider_raises():
    """LLMConfig raises ValidationError for unsupported providers."""
    with pytest.raises(Exception):
        LLMConfig(provider="cohere")


def test_llmconfig_defaults():
    """LLMConfig has sensible defaults."""
    config = LLMConfig()
    assert config.provider == "anthropic"
    assert config.model == "claude-opus-4-6"
    assert config.max_tokens == 512


def test_appconfig_llm_parsed(tmp_path):
    """AppConfig parses llm section into LLMConfig correctly."""
    (tmp_path / "healthchain.yaml").write_text(
        """
llm:
  provider: openai
  model: gpt-4o
  max_tokens: 1024
"""
    )
    config = AppConfig.from_yaml(tmp_path / "healthchain.yaml")

    assert config.llm.provider == "openai"
    assert config.llm.model == "gpt-4o"
    assert config.llm.max_tokens == 1024


def test_appconfig_llm_defaults_to_none(tmp_path):
    """AppConfig.llm is None when not specified in healthchain.yaml."""
    (tmp_path / "healthchain.yaml").write_text("name: minimal-app\n")
    config = AppConfig.from_yaml(tmp_path / "healthchain.yaml")

    assert config.llm is None


def test_appconfig_sources_parsed(tmp_path):
    """AppConfig parses sources section into SourceConfig correctly."""
    (tmp_path / "healthchain.yaml").write_text(
        """
sources:
  medplum:
    env_prefix: MEDPLUM
  epic:
    env_prefix: EPIC
"""
    )
    config = AppConfig.from_yaml(tmp_path / "healthchain.yaml")

    assert "medplum" in config.sources
    assert config.sources["medplum"].env_prefix == "MEDPLUM"
    assert "epic" in config.sources
    assert config.sources["epic"].env_prefix == "EPIC"


def test_appconfig_sources_defaults_to_empty(tmp_path):
    """AppConfig.sources is empty dict when not specified."""
    (tmp_path / "healthchain.yaml").write_text("name: minimal-app\n")
    config = AppConfig.from_yaml(tmp_path / "healthchain.yaml")

    assert config.sources == {}


def test_appconfig_eval_track_events_parsed(tmp_path):
    """AppConfig parses eval.track list correctly."""
    config_file = tmp_path / "healthchain.yaml"
    config_file.write_text(
        """
eval:
  enabled: true
  provider: langfuse
  track:
    - model_inference
    - card_feedback
"""
    )
    config = AppConfig.from_yaml(config_file)

    assert config.eval.enabled is True
    assert config.eval.provider == "langfuse"
    assert "model_inference" in config.eval.track
    assert "card_feedback" in config.eval.track
