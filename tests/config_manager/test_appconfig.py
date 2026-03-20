"""Tests for AppConfig — app-level configuration loaded from healthchain.yaml."""

import pytest

from healthchain.config.appconfig import AppConfig


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
