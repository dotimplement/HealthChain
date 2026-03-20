import argparse
import subprocess
import sys
from pathlib import Path

# ANSI color helpers — consistent with startup banner palette
_RST = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_GREEN = "\033[38;2;0;255;135m"
_CYAN = "\033[38;2;0;215;255m"
_INDIGO = "\033[38;2;99;102;241m"
_PINK = "\033[38;2;255;121;198m"
_AMBER = "\033[38;2;255;180;50m"
_RED = "\033[38;2;255;85;85m"

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

_ENV_EXAMPLE_CDS_HOOKS = """\
# CDS Hooks service — no credentials required to run locally.
# Add FHIR source credentials if your hook fetches patient data.

# FHIR_BASE_URL=
# CLIENT_ID=
# CLIENT_SECRET=

# For JWT assertion flow (e.g. Epic SMART on FHIR)
# CLIENT_SECRET_PATH=/path/to/private_key.pem
"""

_ENV_EXAMPLE_FHIR_GATEWAY = """\
# FHIR source credentials
# Add one block per EHR source. Prefix matches the source name in add_source().

# Epic
EPIC_BASE_URL=https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4
EPIC_CLIENT_ID=
EPIC_CLIENT_SECRET=
# EPIC_CLIENT_SECRET_PATH=/path/to/epic_private_key.pem

# Cerner
CERNER_BASE_URL=https://fhir-open.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d
# Cerner open sandbox requires no credentials

# See docs: https://dotimplement.github.io/HealthChain/reference/gateway/fhir_gateway/
"""

_ENV_EXAMPLE_DEFAULT = """\
# FHIR source credentials
FHIR_BASE_URL=
CLIENT_ID=
CLIENT_SECRET=

# For JWT assertion flow (e.g. Epic SMART on FHIR)
# CLIENT_SECRET_PATH=/path/to/private_key.pem
"""

_REQUIREMENTS = "healthchain\n"

_APP_PY_DEFAULT = """\
# Your HealthChain application goes here.
# See https://dotimplement.github.io/HealthChain/ for examples.
"""

_APP_PY_CDS_HOOKS = """\
from healthchain.gateway import HealthChainAPI
from healthchain.gateway.cds import CDSHooksService
from healthchain.models.requests.cdsrequest import CDSRequest
from healthchain.models.responses.cdsresponse import CDSResponse

app = HealthChainAPI(
    title="My CDS Service",
    description="A CDS Hooks service built with HealthChain",
)

cds = CDSHooksService()


@cds.hook("patient-view", id="my-service", title="My CDS Service")
def patient_view(request: CDSRequest) -> CDSResponse:
    # Add your clinical decision support logic here.
    # request.context contains patient/encounter context from the EHR.
    # request.prefetch contains pre-fetched FHIR resources.
    return CDSResponse(
        cards=[
            {
                "summary": "HealthChain CDS",
                "detail": "Add your clinical logic here.",
                "indicator": "info",
                "source": {"label": "My CDS Service"},
            }
        ]
    )


app.register_service(cds)
"""

_APP_PY_FHIR_GATEWAY = """\
import os
from typing import List

from fhir.resources.bundle import Bundle
from fhir.resources.condition import Condition

from healthchain.gateway import FHIRGateway, HealthChainAPI
from healthchain.fhir import merge_bundles
from healthchain.io.containers import Document
from healthchain.pipeline import Pipeline

# Add FHIR source credentials to .env (see .env.example)
gateway = FHIRGateway()

epic_url = os.getenv("EPIC_BASE_URL")
cerner_url = os.getenv("CERNER_BASE_URL")

if epic_url:
    gateway.add_source("epic", epic_url)
if cerner_url:
    gateway.add_source("cerner", cerner_url)

# Add your NLP/ML/LLM processing steps here
pipeline = Pipeline[Document]()


@pipeline.add_node
def process(doc: Document) -> Document:
    return doc


@gateway.aggregate(Condition)
def get_patient_conditions(patient_id: str, sources: List[str]) -> Bundle:
    \"\"\"Aggregate conditions for a patient from all configured FHIR sources.\"\"\"
    bundles = []
    for source in sources:
        try:
            bundle = gateway.search(
                Condition,
                {"patient": patient_id},
                source,
                add_provenance=True,
            )
            bundles.append(bundle)
        except Exception as e:
            print(f"Error from {source}: {e}")

    merged = merge_bundles(bundles, deduplicate=True)
    doc = pipeline(Document(data=merged))
    return doc.fhir.bundle


app = HealthChainAPI(
    title="My FHIR Gateway",
    description="A multi-EHR data aggregation service built with HealthChain",
)
app.register_gateway(gateway)
"""


def _make_healthchain_yaml(name: str, service_type: str) -> str:
    return f"""\
# HealthChain application configuration
# https://dotimplement.github.io/HealthChain/reference/config

name: {name}
version: "1.0.0"

# Service settings — read by `healthchain serve`
service:
  type: {service_type}
  port: 8000

# Data paths used by your app and sandbox
data:
  patients_dir: ./data
  output_dir: ./output

# Security controls
security:
  auth: none              # none | api-key | smart-on-fhir (planned)
  tls:
    enabled: false
    cert_path: ./certs/server.crt
    key_path: ./certs/server.key
  allowed_origins:
    - "*"

# Compliance settings
compliance:
  hipaa: false            # set true to activate audit logging
  audit_log: ./logs/audit.jsonl

# Evaluation and model monitoring
eval:
  enabled: false
  provider: mlflow        # mlflow | langfuse | none
  tracking_uri: ./mlruns
  track:
    - model_inference
    - cds_card_returned
    - card_feedback

# Site / deployment metadata
site:
  name: ""
  environment: development  # development | staging | production
"""


def new_project(name: str, template: str):
    """Scaffold a new HealthChain project."""
    project_dir = Path(name)

    if project_dir.exists():
        print(f"Error: directory '{name}' already exists.")
        return

    project_dir.mkdir()

    _app_py = {
        "cds-hooks": _APP_PY_CDS_HOOKS,
        "fhir-gateway": _APP_PY_FHIR_GATEWAY,
        "default": _APP_PY_DEFAULT,
    }
    _env_example = {
        "cds-hooks": _ENV_EXAMPLE_CDS_HOOKS,
        "fhir-gateway": _ENV_EXAMPLE_FHIR_GATEWAY,
        "default": _ENV_EXAMPLE_DEFAULT,
    }
    service_type = template if template != "default" else "cds-hooks"

    (project_dir / "app.py").write_text(_app_py[template])
    (project_dir / "healthchain.yaml").write_text(
        _make_healthchain_yaml(name, service_type)
    )
    (project_dir / ".env.example").write_text(_env_example[template])
    (project_dir / "requirements.txt").write_text(_REQUIREMENTS)
    (project_dir / "Dockerfile").write_text(_DOCKERFILE)
    (project_dir / ".dockerignore").write_text(_DOCKERIGNORE)

    print(f"\n{_BOLD}{_GREEN}✚ Created project '{name}/'{_RST}")
    print(f"  {_CYAN}{name}/app.py{_RST}")
    print(f"  {_CYAN}{name}/healthchain.yaml{_RST}")
    print(f"  {_CYAN}{name}/.env.example{_RST}")
    print(f"  {_CYAN}{name}/requirements.txt{_RST}")
    print(f"  {_CYAN}{name}/Dockerfile{_RST}")
    print(f"\n{_BOLD}Next steps:{_RST}")
    print(f"  {_BOLD}cd {name}{_RST}")
    if template == "cds-hooks":
        print(
            f"  {_BOLD}healthchain serve{_RST}          {_DIM}# starts the CDS Hooks service{_RST}"
        )
        print(f"  {_BOLD}open http://localhost:8000/docs{_RST}")
    elif template == "fhir-gateway":
        print(
            f"  {_BOLD}cp .env.example .env{_RST}       {_DIM}# fill in your FHIR source credentials{_RST}"
        )
        print(
            f"  {_BOLD}healthchain serve{_RST}          {_DIM}# starts the FHIR gateway{_RST}"
        )
        print(f"  {_BOLD}open http://localhost:8000/docs{_RST}")
    else:
        print(f"  {_DIM}# Pick a template to get started:{_RST}")
        print(f"  {_BOLD}healthchain new my-app --template cds-hooks{_RST}")
        print(f"  {_BOLD}healthchain new my-app --template fhir-gateway{_RST}")
    print(f"\n{_INDIGO}Configure your app in healthchain.yaml{_RST}")
    print(f"{_DIM}See https://dotimplement.github.io/HealthChain/ for examples.{_RST}")


def eject_templates(target_dir: str):
    """Eject built-in interop templates for customization."""
    try:
        from healthchain.interop import init_config_templates

        target_path = init_config_templates(target_dir)
        print(f"\n{_GREEN}✓ Templates ejected to: {_BOLD}{target_path}{_RST}")
        print(f"\n{_BOLD}Next steps:{_RST}")
        print("  1. Customize the templates in the created directory")
        print("  2. Use them in your code:")
        print(f"     {_DIM}from healthchain.interop import create_interop{_RST}")
        print(f"     {_DIM}engine = create_interop(config_dir='{target_dir}'){_RST}")
        print(
            f"\n{_DIM}See https://dotimplement.github.io/HealthChain/reference/interop/ for details.{_RST}"
        )

    except FileExistsError as e:
        print(f"\n{_RED}Error: {str(e)}{_RST}")
        print(
            f"{_DIM}Choose a different directory name or remove the existing one.{_RST}"
        )
    except Exception as e:
        print(f"\n{_RED}Error ejecting templates: {str(e)}{_RST}")
        print(f"{_DIM}Make sure HealthChain is properly installed.{_RST}")


def serve(app_module: str, host: str, port: int | None):
    """Start a HealthChain app with uvicorn."""
    from healthchain.config.appconfig import AppConfig

    config = AppConfig.load()

    # Resolve port: CLI arg > config > default
    resolved_port = (
        port if port is not None else (config.service.port if config else 8000)
    )

    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        app_module,
        "--host",
        host,
        "--port",
        str(resolved_port),
    ]

    if config and config.security.tls.enabled:
        cmd += [
            "--ssl-certfile",
            config.security.tls.cert_path,
            "--ssl-keyfile",
            config.security.tls.key_path,
        ]

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Server error: {e}")
    except KeyboardInterrupt:
        pass


def sandbox_run(
    url: str,
    workflow: str,
    size: int,
    from_path: str | None,
    output: str | None,
    no_save: bool,
):
    """Fire test requests at a running HealthChain service."""
    from healthchain.config.appconfig import AppConfig
    from healthchain.sandbox import SandboxClient

    config = AppConfig.load()
    resolved_output = output or (config.data.output_dir if config else "./output")

    print(f"\n{_BOLD}{_CYAN}◆ Sandbox{_RST}  {_DIM}{url}{_RST}")
    print(f"  {_CYAN}workflow  {_RST}{workflow}")

    try:
        client = SandboxClient(url=url, workflow=workflow)
    except ValueError as e:
        print(f"\n{_RED}Error:{_RST} {e}")
        return

    if from_path:
        print(f"\n{_DIM}Loading from {from_path}...{_RST}")
        try:
            client.load_from_path(from_path)
        except (FileNotFoundError, ValueError) as e:
            print(f"{_RED}Error loading data:{_RST} {e}")
            return
    else:
        print(f"\n{_DIM}Generating {size} synthetic request(s)...{_RST}")
        try:
            client.load_synthetic(n=size)
        except ValueError as e:
            print(f"{_RED}Error generating synthetic data:{_RST} {e}")
            return

    print(f"{_DIM}Sending {len(client.requests)} request(s) to service...{_RST}\n")

    try:
        responses = client.send_requests()
    except RuntimeError as e:
        print(f"{_RED}Error:{_RST} {e}")
        return

    # Print response summary
    success = sum(1 for r in responses if r)
    result_col = _GREEN if success == len(responses) else _AMBER
    print(
        f"{_BOLD}Results:{_RST} {result_col}{success}/{len(responses)} successful{_RST}\n"
    )

    indicator_colours = {
        "INFO": _CYAN,
        "WARNING": _AMBER,
        "CRITICAL": _RED,
        "SUCCESS": _GREEN,
    }
    for i, response in enumerate(responses):
        cards = response.get("cards", [])
        if not cards:
            print(f"  {_DIM}[{i + 1}] no cards returned{_RST}")
            continue
        print(f"  {_BOLD}[{i + 1}]{_RST} {len(cards)} card(s)")
        for card in cards:
            indicator = card.get("indicator", "info").upper()
            summary = card.get("summary", "")
            ind_col = indicator_colours.get(indicator, _DIM)
            print(f"      {ind_col}{indicator}{_RST}  {summary}")

    if not no_save:
        client.save_results(resolved_output)
        print(f"\n{_GREEN}✓{_RST} Saved to {_BOLD}{resolved_output}/{_RST}")


def status():
    """Show current project status from healthchain.yaml."""
    from healthchain.config.appconfig import AppConfig

    config = AppConfig.load()

    if config is None:
        print(f"\n{_AMBER}No healthchain.yaml found in current directory.{_RST}")
        print(f"Run {_BOLD}healthchain new <name>{_RST} to scaffold a project.")
        return

    def _key(k: str) -> str:
        return f"  {_CYAN}{k}{_RST}"

    def _val_on(v: str) -> str:
        return f"{_GREEN}{v}{_RST}"

    def _val_off(v: str) -> str:
        return f"{_RED}{v}{_RST}"

    def _val_env(e: str) -> str:
        c = {
            "production": _GREEN,
            "staging": _CYAN,
            "development": _AMBER,
        }.get(e, _RST)
        return f"{c}{e}{_RST}"

    def _section(s: str) -> str:
        return f"\n{_BOLD}{_INDIGO}{s}{_RST}"

    print(
        f"\n{_BOLD}{_PINK}✚ HealthChain{_RST}  "
        f"{_BOLD}{config.name}{_RST}  {_DIM}v{config.version}{_RST}"
    )
    print(f"{_INDIGO}{'─' * 40}{_RST}")

    print(_section("Service"))
    print(f"{_key('type        ')}{config.service.type}")
    print(f"{_key('port        ')}{_BOLD}{config.service.port}{_RST}")

    print(_section("Site"))
    print(f"{_key('environment ')}{_val_env(config.site.environment)}")
    if config.site.name:
        print(f"{_key('name        ')}{config.site.name}")

    print(_section("Security"))
    auth_col = _GREEN if config.security.auth != "none" else _AMBER
    print(f"{_key('auth        ')}{auth_col}{config.security.auth}{_RST}")
    tls_val = (
        _val_on("enabled") if config.security.tls.enabled else _val_off("disabled")
    )
    print(f"{_key('TLS         ')}{tls_val}")
    origins = ", ".join(config.security.allowed_origins)
    print(f"{_key('origins     ')}{_DIM}{origins}{_RST}")

    print(_section("Compliance"))
    hipaa_val = _val_on("enabled") if config.compliance.hipaa else _val_off("disabled")
    print(f"{_key('HIPAA       ')}{hipaa_val}")
    if config.compliance.hipaa:
        print(f"{_key('audit log   ')}{_BOLD}{config.compliance.audit_log}{_RST}")

    print(_section("Eval"))
    if config.eval.enabled:
        print(f"{_key('provider    ')}{config.eval.provider}")
        print(f"{_key('tracking    ')}{_BOLD}{config.eval.tracking_uri}{_RST}")
        print(f"{_key('events      ')}{_DIM}{', '.join(config.eval.track)}{_RST}")
    else:
        print(f"  {_DIM}disabled{_RST}")

    print()


def main():
    parser = argparse.ArgumentParser(
        description=(
            f"{_BOLD}{_CYAN}✚ HealthChain{_RST}  {_DIM}Open-Source Healthcare AI{_RST}\n"
            f"{_INDIGO}{'─' * 40}{_RST}"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subparser for the 'new' command
    new_parser = subparsers.add_parser("new", help="Scaffold a new HealthChain project")
    new_parser.add_argument("name", type=str, help="Project name (creates a directory)")
    new_parser.add_argument(
        "--type",
        "-t",
        type=str,
        default="default",
        choices=["cds-hooks", "fhir-gateway", "default"],
        help="Project type (default: empty stub)",
        dest="template",
    )

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
        "--port",
        type=int,
        default=None,
        help="Port (default: from healthchain.yaml or 8000)",
    )

    # Subparser for the 'sandbox' command
    sandbox_parser = subparsers.add_parser(
        "sandbox", help="Send test requests to a running HealthChain service"
    )
    sandbox_subparsers = sandbox_parser.add_subparsers(
        dest="sandbox_command", required=True
    )
    sandbox_run_parser = sandbox_subparsers.add_parser(
        "run", help="Fire test requests at a service"
    )
    sandbox_run_parser.add_argument(
        "--url",
        type=str,
        required=True,
        help="Full service URL (e.g. http://localhost:8000/cds/cds-services/my-service)",
    )
    sandbox_run_parser.add_argument(
        "--workflow",
        type=str,
        default="patient-view",
        choices=["patient-view", "order-select", "order-sign", "encounter-discharge"],
        help="CDS workflow to simulate (default: patient-view)",
    )
    sandbox_run_parser.add_argument(
        "--size",
        type=int,
        default=3,
        help="Number of synthetic requests to generate (default: 3)",
    )
    sandbox_run_parser.add_argument(
        "--from-path",
        type=str,
        default=None,
        metavar="PATH",
        help="Load requests from a file or directory instead of generating synthetic data",
    )
    sandbox_run_parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Directory to save results (default: from healthchain.yaml or ./output)",
    )
    sandbox_run_parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save results to disk",
    )

    # Subparser for the 'status' command
    subparsers.add_parser("status", help="Show project status from healthchain.yaml")

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
        new_project(args.name, args.template)
    elif args.command == "serve":
        serve(args.app_module, args.host, args.port)
    elif args.command == "sandbox":
        if args.sandbox_command == "run":
            sandbox_run(
                url=args.url,
                workflow=args.workflow,
                size=args.size,
                from_path=args.from_path,
                output=args.output,
                no_save=args.no_save,
            )
    elif args.command == "status":
        status()
    elif args.command == "eject-templates":
        eject_templates(args.target_dir)


if __name__ == "__main__":
    main()
