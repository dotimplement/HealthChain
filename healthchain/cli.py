import argparse
import subprocess


def run_file(filename):
    try:
        result = subprocess.run(["poetry", "run", "python", filename], check=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while trying to run the file: {e}")


def main():
    parser = argparse.ArgumentParser(description="HealthChain command-line interface")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subparser for the 'run' command
    run_parser = subparsers.add_parser("run", help="Run a specified file")
    run_parser.add_argument("filename", type=str, help="The filename to run")

    args = parser.parse_args()

    if args.command == "run":
        run_file(args.filename)


if __name__ == "__main__":
    main()
