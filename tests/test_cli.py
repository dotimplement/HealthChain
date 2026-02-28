"""Tests for HealthChain CLI functionality."""

import pytest
import subprocess
from unittest.mock import patch

from healthchain.cli import eject_templates, serve, main


@pytest.mark.parametrize(
    "error,expected_messages",
    [
        (
            FileExistsError("Directory already exists"),
            [
                "❌ Error: Directory already exists",
                "💡 Choose a different directory name or remove the existing one",
            ],
        ),
        (
            Exception("Something went wrong"),
            [
                "❌ Error ejecting templates: Something went wrong",
                "💡 Make sure HealthChain is properly installed",
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

    # Verify helpful error messages are displayed
    for expected_msg in expected_messages:
        assert any(expected_msg in str(call) for call in mock_print.call_args_list)


@patch("healthchain.interop.init_config_templates")
def test_eject_templates_success_provides_usage_instructions(mock_init_templates):
    """eject_templates provides clear usage instructions when successful."""
    target_dir = "./test_configs"
    mock_init_templates.return_value = target_dir

    with patch("builtins.print") as mock_print:
        eject_templates(target_dir)

    # Verify success message and usage instructions are provided
    print_output = " ".join(str(call) for call in mock_print.call_args_list)
    assert "✅ Templates ejected to:" in print_output
    assert "create_interop(config_dir=" in print_output
    assert "Next steps:" in print_output


@patch("subprocess.run")
def test_serve_handles_execution_errors_gracefully(mock_run):
    """serve provides clear error message when server fails to start."""
    mock_run.side_effect = subprocess.CalledProcessError(1, "uvicorn")

    with patch("builtins.print") as mock_print:
        serve("app:app", "0.0.0.0", 8000)

    # Verify error message is informative
    error_message = mock_print.call_args[0][0]
    assert "❌ Server error:" in error_message


@pytest.mark.parametrize(
    "args,expected_call",
    [
        (
            ["healthchain", "serve", "test.py:app"],
            ("serve", ("test.py:app", "0.0.0.0", 8000)),
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
