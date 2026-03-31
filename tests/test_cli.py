"""Tests for HealthChain CLI functionality."""

import pytest
import subprocess
from unittest.mock import patch, MagicMock

from healthchain.cli import eject_templates, new_project, serve, status, main


@pytest.mark.parametrize(
    "error,expected_messages",
    [
        (
            FileExistsError("Directory already exists"),
            [
                "Error: Directory already exists",
                "Choose a different directory name or remove the existing one",
            ],
        ),
        (
            Exception("Something went wrong"),
            [
                "Error ejecting templates: Something went wrong",
                "Make sure HealthChain is properly installed",
            ],
        ),
    ],
)
@patch("healthchain.interop.init_config_templates")
def test_eject_templates_error_handling_provides_helpful_guidance(
    mock_init_templates, error, expected_messages
):
    """eject_templates provides helpful error messages and guidance when template creation fails."""
    mock_init_templates.side_effect = error

    with patch("builtins.print") as mock_print:
        eject_templates("./test_configs")

    for expected_msg in expected_messages:
        assert any(expected_msg in str(call) for call in mock_print.call_args_list)


@patch("healthchain.interop.init_config_templates")
def test_eject_templates_success_provides_usage_instructions(mock_init_templates):
    """eject_templates provides clear usage instructions when successful."""
    target_dir = "./test_configs"
    mock_init_templates.return_value = target_dir

    with patch("builtins.print") as mock_print:
        eject_templates(target_dir)

    print_output = " ".join(str(call) for call in mock_print.call_args_list)
    assert "Templates ejected to:" in print_output
    assert "create_interop(config_dir=" in print_output
    assert "Next steps:" in print_output


@patch("subprocess.run")
@patch("healthchain.config.appconfig.AppConfig.load", return_value=None)
def test_serve_handles_execution_errors_gracefully(mock_config, mock_run):
    """serve provides clear error message when server fails to start."""
    mock_run.side_effect = subprocess.CalledProcessError(1, "uvicorn")

    with patch("builtins.print") as mock_print:
        serve("app:app", "0.0.0.0", None)

    error_message = mock_print.call_args[0][0]
    assert "❌ Server error:" in error_message


@patch("subprocess.run")
@patch("healthchain.config.appconfig.AppConfig.load")
def test_serve_reads_port_from_config(mock_load, mock_run):
    """serve uses port from healthchain.yaml when --port is not provided."""
    mock_config = MagicMock()
    mock_config.service.port = 9000
    mock_config.security.tls.enabled = False
    mock_load.return_value = mock_config

    serve("app:app", "0.0.0.0", None)

    call_args = mock_run.call_args[0][0]
    assert "--port" in call_args
    assert "9000" in call_args


@patch("subprocess.run")
@patch("healthchain.config.appconfig.AppConfig.load")
def test_serve_cli_port_overrides_config(mock_load, mock_run):
    """serve uses --port flag value over healthchain.yaml port."""
    mock_config = MagicMock()
    mock_config.service.port = 9000
    mock_config.security.tls.enabled = False
    mock_load.return_value = mock_config

    serve("app:app", "0.0.0.0", 8080)

    call_args = mock_run.call_args[0][0]
    assert "8080" in call_args
    assert "9000" not in call_args


@patch("subprocess.run")
@patch("healthchain.config.appconfig.AppConfig.load", return_value=None)
def test_serve_defaults_to_8000_without_config(mock_load, mock_run):
    """serve defaults to port 8000 when no config and no --port flag."""
    serve("app:app", "0.0.0.0", None)

    call_args = mock_run.call_args[0][0]
    assert "8000" in call_args


@patch("subprocess.run")
@patch("healthchain.config.appconfig.AppConfig.load")
def test_serve_passes_tls_args_when_enabled(mock_load, mock_run):
    """serve passes ssl-certfile and ssl-keyfile to uvicorn when TLS is enabled."""
    mock_config = MagicMock()
    mock_config.service.port = 8000
    mock_config.security.tls.enabled = True
    mock_config.security.tls.cert_path = "./certs/cert.pem"
    mock_config.security.tls.key_path = "./certs/key.pem"
    mock_load.return_value = mock_config

    serve("app:app", "0.0.0.0", None)

    call_args = mock_run.call_args[0][0]
    assert "--ssl-certfile" in call_args
    assert "--ssl-keyfile" in call_args


def test_new_project_creates_expected_files(tmp_path):
    """new_project creates all expected files in a new directory."""
    project_dir = tmp_path / "my-app"

    with patch("builtins.print"):
        new_project(str(project_dir), "default")

    assert (project_dir / "app.py").exists()
    assert (project_dir / "healthchain.yaml").exists()
    assert (project_dir / ".env.example").exists()
    assert (project_dir / "requirements.txt").exists()
    assert (project_dir / "Dockerfile").exists()


def test_new_project_cds_hooks_template_generates_working_app(tmp_path):
    """new_project with cds-hooks template generates a non-empty app.py with CDS imports."""
    project_dir = tmp_path / "my-cds-app"

    with patch("builtins.print"):
        new_project(str(project_dir), "cds-hooks")

    app_py = (project_dir / "app.py").read_text()
    assert "CDSHooksService" in app_py
    assert "CDSResponse" in app_py
    assert "HealthChainAPI" in app_py


def test_new_project_fhir_gateway_template_generates_working_app(tmp_path):
    """new_project with fhir-gateway template generates a non-empty app.py with gateway imports."""
    project_dir = tmp_path / "my-fhir-app"

    with patch("builtins.print"):
        new_project(str(project_dir), "fhir-gateway")

    app_py = (project_dir / "app.py").read_text()
    assert "FHIRGateway" in app_py
    assert "HealthChainAPI" in app_py
    assert "merge_bundles" in app_py


def test_new_project_default_template_generates_stub(tmp_path):
    """new_project with default template generates a minimal stub app.py."""
    project_dir = tmp_path / "my-stub-app"

    with patch("builtins.print"):
        new_project(str(project_dir), "default")

    app_py = (project_dir / "app.py").read_text()
    assert "CDSHooksService" not in app_py
    assert "FHIRGateway" not in app_py


def test_new_project_yaml_contains_project_name(tmp_path):
    """new_project writes the project name into healthchain.yaml."""
    project_dir = tmp_path / "named-app"

    with patch("builtins.print"):
        new_project(str(project_dir), "default")

    yaml_content = (project_dir / "healthchain.yaml").read_text()
    assert "named-app" in yaml_content


def test_new_project_rejects_existing_directory(tmp_path):
    """new_project prints an error and does not overwrite an existing directory."""
    project_dir = tmp_path / "existing-app"
    project_dir.mkdir()

    with patch("builtins.print") as mock_print:
        new_project(str(project_dir), "default")

    print_output = " ".join(str(call) for call in mock_print.call_args_list)
    assert "already exists" in print_output


@patch("healthchain.config.appconfig.AppConfig.load", return_value=None)
def test_status_with_no_config_prints_helpful_message(mock_load):
    """status prints a helpful message when healthchain.yaml is not found."""
    with patch("builtins.print") as mock_print:
        status()

    print_output = " ".join(str(call) for call in mock_print.call_args_list)
    assert "healthchain.yaml" in print_output


@patch("healthchain.config.appconfig.AppConfig.load")
def test_status_displays_config_fields(mock_load):
    """status prints key config values from healthchain.yaml."""
    mock_config = MagicMock()
    mock_config.name = "test-app"
    mock_config.version = "1.0.0"
    mock_config.service.type = "cds-hooks"
    mock_config.service.port = 8000
    mock_config.site.environment = "production"
    mock_config.site.name = "Test Hospital"
    mock_config.security.auth = "none"
    mock_config.security.tls.enabled = False
    mock_config.security.allowed_origins = ["*"]
    mock_config.compliance.hipaa = True
    mock_config.compliance.audit_log = "./logs/audit.jsonl"
    mock_config.eval.enabled = False
    mock_load.return_value = mock_config

    with patch("builtins.print") as mock_print:
        status()

    print_output = " ".join(str(call) for call in mock_print.call_args_list)
    assert "test-app" in print_output
    assert "cds-hooks" in print_output
    assert "production" in print_output
    assert "Test Hospital" in print_output
    assert "enabled" in print_output


@pytest.mark.parametrize(
    "args,expected_call",
    [
        (
            ["healthchain", "serve", "test.py:app"],
            ("serve", ("test.py:app", "0.0.0.0", None)),
        ),
        (
            ["healthchain", "eject-templates", "my_configs"],
            ("eject_templates", ("my_configs",)),
        ),
        (
            ["healthchain", "eject-templates"],
            ("eject_templates", ("./healthchain_configs",)),
        ),
    ],
)
def test_main_routes_commands_correctly(args, expected_call):
    """Main function correctly routes CLI commands to appropriate handlers."""
    function_name, expected_args = expected_call

    with patch(f"healthchain.cli.{function_name}") as mock_function:
        with patch("sys.argv", args):
            main()
            mock_function.assert_called_once_with(*expected_args)


def test_main_requires_command_argument():
    """Main function enforces required command argument."""
    with patch("sys.argv", ["healthchain"]):
        with pytest.raises(SystemExit):
            main()
