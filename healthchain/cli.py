import argparse
import subprocess
import sys
from pathlib import Path

_DOCKERFILE = """\
# HealthChain application Dockerfile
#
# Usage:
#   Build:  docker build -t my-healthcare-app .
#   Run:    docker run -p 8000:8000 --env-file .env my-healthcare-app
#
# Required environment variables (set in .env or pass via -e):
#   APP_MODULE   Python module path to your app, e.g. "myapp:app" (default: "app:app")
#
# FHIR source credentials (if connecting to Epic/Cerner):
#   FHIR_BASE_URL, CLIENT_ID, CLIENT_SECRET or CLIENT_SECRET_PATH
#
# See docs: https://dotimplement.github.io/HealthChain/reference/gateway/gateway/

FROM python:3.11-slim

# Keeps Python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1 \\
    PYTHONDONTWRITEBYTECODE=1 \\
    APP_MODULE=app:app \\
    PORT=8000

WORKDIR /app

# Install system dependencies needed by lxml and spaCy
RUN apt-get update && apt-get install -y --no-install-recommends \\
    gcc \\
    g++ \\
    && rm -rf /var/lib/apt/lists/*

# Install healthchain from PyPI
RUN pip install --no-cache-dir healthchain

# Install any additional dependencies your application needs
# (copy requirements first to leverage Docker layer caching)
COPY requirements.txt* ./
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# Copy application code
COPY . .

# Run as non-root user
RUN useradd -m appuser && chown -R appuser /app
USER appuser

EXPOSE $PORT

CMD uvicorn $APP_MODULE --host 0.0.0.0 --port $PORT
"""

_DOCKERIGNORE = """\
.git
.idea
.pytest_cache
.ruff_cache
__pycache__
*.pyc
*.pyo
*.pyd
.env
.env.*
tests/
docs/
notebooks/
output/
*.md
!README.md
"""

_ENV_EXAMPLE = """\
# FHIR source credentials
FHIR_BASE_URL=
CLIENT_ID=
CLIENT_SECRET=

# For JWT assertion flow (e.g. Epic SMART on FHIR)
# CLIENT_SECRET_PATH=/path/to/private_key.pem
"""

_REQUIREMENTS = "healthchain\n"

_APP_PY = """\
# Your HealthChain application goes here.
# See https://dotimplement.github.io/HealthChain/ for examples.
"""


def new_project(name: str):
    """Scaffold a new HealthChain project."""
    project_dir = Path(name)

    if project_dir.exists():
        print(f"❌ Directory '{name}' already exists.")
        return

    project_dir.mkdir()
    (project_dir / "app.py").write_text(_APP_PY)
    (project_dir / ".env.example").write_text(_ENV_EXAMPLE)
    (project_dir / "requirements.txt").write_text(_REQUIREMENTS)
    (project_dir / "Dockerfile").write_text(_DOCKERFILE)
    (project_dir / ".dockerignore").write_text(_DOCKERIGNORE)

    print(f"\nCreated project '{name}/'")
    print(f"  {name}/app.py")
    print(f"  {name}/.env.example")
    print(f"  {name}/requirements.txt")
    print(f"  {name}/Dockerfile")
    print("\nNext steps:")
    print(f"  1. Build your app in {name}/app.py")
    print("  2. Copy .env.example to .env and fill in your credentials")
    print(f"  3. healthchain serve app:app  (from inside {name}/)")
    print(f"  4. docker build -t {name} {name}/")
    print(f"  5. docker run -p 8000:8000 --env-file {name}/.env {name}")
    print("\nUsing format conversion? Run: healthchain eject-templates ./configs")
    print("See https://dotimplement.github.io/HealthChain/ for examples.")


def eject_templates(target_dir: str):
    """Eject built-in interop templates for customization."""
    try:
        from healthchain.interop import init_config_templates

        target_path = init_config_templates(target_dir)
        print(f"\n✅ Templates ejected to: {target_path}")
        print("\nNext steps:")
        print("  1. Customize the templates in the created directory")
        print("  2. Use them in your code:")
        print("     from healthchain.interop import create_interop")
        print(f"     engine = create_interop(config_dir='{target_dir}')")
        print(
            "\nSee https://dotimplement.github.io/HealthChain/reference/interop/ for details."
        )

    except FileExistsError as e:
        print(f"❌ Error: {str(e)}")
        print("💡 Choose a different directory name or remove the existing one.")
    except Exception as e:
        print(f"❌ Error ejecting templates: {str(e)}")
        print("💡 Make sure HealthChain is properly installed.")


def serve(app_module: str, host: str, port: int):
    """Start a HealthChain app with uvicorn."""
    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "uvicorn",
                app_module,
                "--host",
                host,
                "--port",
                str(port),
            ],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"❌ Server error: {e}")
    except KeyboardInterrupt:
        pass


def main():
    parser = argparse.ArgumentParser(description="HealthChain command-line interface")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subparser for the 'new' command
    new_parser = subparsers.add_parser("new", help="Scaffold a new HealthChain project")
    new_parser.add_argument("name", type=str, help="Project name (creates a directory)")

    # Subparser for the 'serve' command
    serve_parser = subparsers.add_parser(
        "serve", help="Start a HealthChain app with uvicorn"
    )
    serve_parser.add_argument(
        "app_module",
        type=str,
        nargs="?",
        default="app:app",
        help="Module path to your app (default: app:app)",
    )
    serve_parser.add_argument(
        "--host", type=str, default="0.0.0.0", help="Host (default: 0.0.0.0)"
    )
    serve_parser.add_argument(
        "--port", type=int, default=8000, help="Port (default: 8000)"
    )

    # Subparser for the 'eject-templates' command
    eject_parser = subparsers.add_parser(
        "eject-templates",
        help="Eject built-in interop templates for customization",
    )
    eject_parser.add_argument(
        "target_dir",
        type=str,
        nargs="?",
        default="./healthchain_configs",
        help="Directory to eject templates into (default: ./healthchain_configs)",
    )

    args = parser.parse_args()

    if args.command == "new":
        new_project(args.name)
    elif args.command == "serve":
        serve(args.app_module, args.host, args.port)
    elif args.command == "eject-templates":
        eject_templates(args.target_dir)


if __name__ == "__main__":
    main()
