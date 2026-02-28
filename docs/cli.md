# CLI Reference

HealthChain ships with a CLI to help you scaffold, run, and customize projects.

```bash
healthchain --help
```

---

## `healthchain new`

Scaffold a new project directory with everything you need to get started.

```bash
healthchain new my-app
```

Creates:

```
my-app/
├── app.py            # your application entry point
├── .env.example      # FHIR credential template — copy to .env and fill in
├── requirements.txt  # add extra dependencies here
├── Dockerfile
└── .dockerignore
```

---

## `healthchain serve`

Start your app locally with uvicorn.

```bash
healthchain serve              # defaults to app:app on port 8000
healthchain serve app:app
healthchain serve app:app --port 8080
healthchain serve app:app --host 127.0.0.1 --port 8080
```

The `app_module` argument is the Python import path to your FastAPI app instance — `<module>:<variable>`. If your app is defined as `app = HealthChainAPI()` in `app.py`, the default `app:app` works as-is.

To run in Docker instead:

```bash
docker build -t my-app .
docker run -p 8000:8000 --env-file .env my-app
```

---

## `healthchain eject-templates`

Copy the built-in interop templates into your project so you can customize them.

```bash
healthchain eject-templates ./my_configs
```

Only needed if you're using the [InteropEngine](reference/interop/interop.md) and want to customize FHIR↔CDA conversion beyond the defaults. After ejecting:

```python
from healthchain.interop import create_interop

engine = create_interop(config_dir="./my_configs")
```

See [Interoperability](reference/interop/interop.md) for details.

---

## Typical workflow

```bash
# 1. Scaffold a new project
healthchain new my-cds-service
cd my-cds-service

# 2. Build your app in app.py
#    See https://dotimplement.github.io/HealthChain/cookbook/ for examples

# 3. Set credentials
cp .env.example .env
# edit .env with your FHIR_BASE_URL, CLIENT_ID, CLIENT_SECRET

# 4. Run locally
healthchain serve

# 5. Ship it
docker build -t my-cds-service .
docker run -p 8000:8000 --env-file .env my-cds-service
```
