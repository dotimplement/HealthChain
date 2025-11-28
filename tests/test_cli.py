"""Tests for HealthChain CLI functionality."""

import pytest
import subprocess
from unittest.mock import patch

from healthchain.cli import init_configs, run_file, main


@pytest.mark.parametrize(
    "error,expected_messages",
    [
        (
            FileExistsError("Directory already exists"),
            [
                "❌ Error: Directory already exists",
                "💡 Tip: Choose a different directory name or remove the existing one",
            ],
        ),
        (
            Exception("Something went wrong"),
            [
                "❌ Error initializing configs: Something went wrong",
                "💡 Tip: Make sure HealthChain is properly installed",
            ],
        ),
    ],
)
@patch("healthchain.interop.init_config_templates")
def test_init_configs_error_handling_provides_helpful_guidance(
    mock_init_templates, error, expected_messages
):
    """init_configs provides helpful error messages and guidance when template creation fails."""
    mock_init_templates.side_effect = error

    with patch("builtins.print") as mock_print:
        init_configs("./test_configs")

    # Verify helpful error messages are displayed
    for expected_msg in expected_messages:
        assert any(expected_msg in str(call) for call in mock_print.call_args_list)


@patch("healthchain.interop.init_config_templates")
def test_init_configs_success_provides_usage_instructions(mock_init_templates):
    """init_configs provides clear usage instructions when successful."""
    target_dir = "./test_configs"
    mock_init_templates.return_value = target_dir

    with patch("builtins.print") as mock_print:
        init_configs(target_dir)

    # Verify success message and usage instructions are provided
    print_output = " ".join(str(call) for call in mock_print.call_args_list)
    assert "🎉 Success!" in print_output
    assert "create_interop(config_dir=" in print_output
    assert "📖 Next steps:" in print_output


@patch("subprocess.run")
def test_run_file_handles_execution_errors_gracefully(mock_run):
    """run_file provides clear error message when script execution fails."""
    mock_run.side_effect = subprocess.CalledProcessError(1, "uv")

    with patch("builtins.print") as mock_print:
        run_file("failing_script.py")

    # Verify error message is informative
    error_message = mock_print.call_args[0][0]
    assert "An error occurred while trying to run the file:" in error_message


@pytest.mark.parametrize(
    "args,expected_call",
    [
        (["healthchain", "run", "test.py"], ("run_file", "test.py")),
        (["healthchain", "init-configs", "my_configs"], ("init_configs", "my_configs")),
        (["healthchain", "init-configs"], ("init_configs", "./healthchain_configs")),
    ],
)
def test_main_routes_commands_correctly(args, expected_call):
    """Main function correctly routes CLI commands to appropriate handlers."""
    function_name, expected_arg = expected_call

    with patch(f"healthchain.cli.{function_name}") as mock_function:
        with patch("sys.argv", args):
            main()
            mock_function.assert_called_once_with(expected_arg)


def test_main_requires_command_argument():
    """Main function enforces required command argument."""
    with patch("sys.argv", ["healthchain"]):
        with pytest.raises(SystemExit):
            main()
