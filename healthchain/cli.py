import argparse
import subprocess


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

    args = parser.parse_args()

    if args.command == "run":
        run_file(args.filename)
    elif args.command == "init-configs":
        init_configs(args.target_dir)


if __name__ == "__main__":
    main()
