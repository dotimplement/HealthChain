import argparse
import subprocess
import sys


def run_file(filename):
    try:
        result = subprocess.run(["uv", "run", "python", filename], check=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while trying to run the file: {e}")


def init_configs(target_dir: str):
    """Initialize configuration templates for customization."""
    try:
        from healthchain.interop import init_config_templates

        target_path = init_config_templates(target_dir)
        print(f"\n🎉 Success! Configuration templates created at: {target_path}")
        print("\n📖 Next steps:")
        print("  1. Customize the configuration files in the created directory")
        print("  2. Use them in your code:")
        print("     from healthchain.interop import create_interop")
        print(f"     engine = create_interop(config_dir='{target_dir}')")
        print("\n📚 See documentation for configuration options")

    except FileExistsError as e:
        print(f"❌ Error: {str(e)}")
        print("💡 Tip: Choose a different directory name or remove the existing one")
    except Exception as e:
        print(f"❌ Error initializing configs: {str(e)}")
        print("💡 Tip: Make sure HealthChain is properly installed")


def _check_mlflow_installed():
    """Check if MLFlow is installed and provide helpful error if not."""
    try:
        from healthchain.mlflow import is_mlflow_available

        if not is_mlflow_available():
            print("❌ MLFlow is not installed.")
            print("💡 Install it with: pip install healthchain[mlflow]")
            sys.exit(1)
    except ImportError:
        print("❌ MLFlow module not available.")
        print("💡 Install it with: pip install healthchain[mlflow]")
        sys.exit(1)


def mlflow_list_experiments(tracking_uri: str):
    """List all MLFlow experiments."""
    _check_mlflow_installed()

    from healthchain.mlflow import MLFlowConfig, MLFlowTracker

    config = MLFlowConfig(tracking_uri=tracking_uri, experiment_name="default")
    tracker = MLFlowTracker(config)

    experiments = tracker.list_experiments()

    if not experiments:
        print("No experiments found.")
        return

    print(f"\n{'ID':<15} {'Name':<40} {'Stage':<15}")
    print("-" * 70)
    for exp in experiments:
        print(
            f"{exp['experiment_id']:<15} {exp['name']:<40} {exp['lifecycle_stage']:<15}"
        )
    print(f"\nTotal: {len(experiments)} experiment(s)")


def mlflow_list_runs(experiment: str, tracking_uri: str, max_results: int):
    """List runs for an MLFlow experiment."""
    _check_mlflow_installed()

    from healthchain.mlflow import MLFlowConfig, MLFlowTracker

    config = MLFlowConfig(tracking_uri=tracking_uri, experiment_name=experiment)
    tracker = MLFlowTracker(config)

    runs = tracker.list_runs(experiment_name=experiment, max_results=max_results)

    if not runs:
        print(f"No runs found for experiment: {experiment}")
        return

    print(f"\nRuns for experiment: {experiment}")
    print(f"{'Run ID':<36} {'Status':<12} {'Start Time':<25}")
    print("-" * 75)
    for run in runs:
        run_id = run.get("run_id", "N/A")
        status = run.get("status", "N/A")
        start_time = run.get("start_time", "N/A")
        print(f"{run_id:<36} {status:<12} {str(start_time):<25}")
    print(f"\nTotal: {len(runs)} run(s)")


def mlflow_export_model(model_uri: str, output_path: str):
    """Export an MLFlow model to a local path."""
    _check_mlflow_installed()

    try:
        import mlflow

        print(f"Exporting model from: {model_uri}")
        print(f"To: {output_path}")

        # Download the model artifacts
        local_path = mlflow.artifacts.download_artifacts(
            artifact_uri=model_uri, dst_path=output_path
        )

        print(f"\n🎉 Model exported successfully to: {local_path}")
    except Exception as e:
        print(f"❌ Error exporting model: {str(e)}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="HealthChain command-line interface")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subparser for the 'run' command
    run_parser = subparsers.add_parser("run", help="Run a specified file")
    run_parser.add_argument("filename", type=str, help="The filename to run")

    # Subparser for the 'init-configs' command
    init_parser = subparsers.add_parser(
        "init-configs",
        help="Initialize configuration templates for interop customization",
    )
    init_parser.add_argument(
        "target_dir",
        type=str,
        nargs="?",
        default="./healthchain_configs",
        help="Directory to create configuration templates (default: ./healthchain_configs)",
    )

    # Subparser for MLFlow commands
    mlflow_parser = subparsers.add_parser(
        "mlflow",
        help="MLFlow experiment tracking commands",
    )
    mlflow_subparsers = mlflow_parser.add_subparsers(
        dest="mlflow_command",
        required=True,
    )

    # MLFlow list-experiments command
    mlflow_list_exp_parser = mlflow_subparsers.add_parser(
        "list-experiments",
        help="List all MLFlow experiments",
    )
    mlflow_list_exp_parser.add_argument(
        "--tracking-uri",
        type=str,
        default="mlruns",
        help="MLFlow tracking URI (default: mlruns)",
    )

    # MLFlow list-runs command
    mlflow_list_runs_parser = mlflow_subparsers.add_parser(
        "list-runs",
        help="List runs for an MLFlow experiment",
    )
    mlflow_list_runs_parser.add_argument(
        "experiment",
        type=str,
        help="Name of the experiment to list runs for",
    )
    mlflow_list_runs_parser.add_argument(
        "--tracking-uri",
        type=str,
        default="mlruns",
        help="MLFlow tracking URI (default: mlruns)",
    )
    mlflow_list_runs_parser.add_argument(
        "--max-results",
        type=int,
        default=100,
        help="Maximum number of runs to return (default: 100)",
    )

    # MLFlow export-model command
    mlflow_export_parser = mlflow_subparsers.add_parser(
        "export-model",
        help="Export an MLFlow model to a local path",
    )
    mlflow_export_parser.add_argument(
        "model_uri",
        type=str,
        help="MLFlow model URI (e.g., runs:/<run_id>/model)",
    )
    mlflow_export_parser.add_argument(
        "-o",
        "--output",
        type=str,
        required=True,
        help="Output directory path for the exported model",
    )

    args = parser.parse_args()

    if args.command == "run":
        run_file(args.filename)
    elif args.command == "init-configs":
        init_configs(args.target_dir)
    elif args.command == "mlflow":
        if args.mlflow_command == "list-experiments":
            mlflow_list_experiments(args.tracking_uri)
        elif args.mlflow_command == "list-runs":
            mlflow_list_runs(args.experiment, args.tracking_uri, args.max_results)
        elif args.mlflow_command == "export-model":
            mlflow_export_model(args.model_uri, args.output)


if __name__ == "__main__":
    main()
