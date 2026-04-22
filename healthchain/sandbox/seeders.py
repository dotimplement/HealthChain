import json
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import httpx

from healthchain.gateway.clients.fhir.base import FHIRAuthConfig
from healthchain.gateway.clients.auth import OAuth2TokenManager


def _normalise_base_url(raw: str) -> str:
    parsed = urlparse(raw)
    if parsed.scheme == "fhir":
        return urlunparse(("https", parsed.netloc, parsed.path, "", "", "")).rstrip("/")
    if parsed.scheme in {"http", "https"}:
        return urlunparse(
            (parsed.scheme, parsed.netloc, parsed.path, "", "", "")
        ).rstrip("/")
    raise ValueError(
        f"Unsupported URL scheme '{parsed.scheme or '<missing>'}'. "
        "Use https://... or fhir://..."
    )


def _auth_headers(token_manager: OAuth2TokenManager) -> dict:
    return {
        "Authorization": f"Bearer {token_manager.get_access_token()}",
        "Content-Type": "application/fhir+json",
        "Accept": "application/fhir+json",
    }


def _as_transaction_bundle(data: dict | list) -> dict:
    """Normalise arbitrary FHIR JSON to a transaction Bundle."""
    if isinstance(data, dict) and data.get("resourceType") == "Bundle":
        return data
    resources = data if isinstance(data, list) else [data]
    return {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": [
            {
                "resource": r,
                "request": {"method": "POST", "url": r.get("resourceType", "Resource")},
            }
            for r in resources
        ],
    }


def _patient_ids_from_response(response_bundle: dict) -> list[str]:
    """Extract server-assigned Patient IDs from a transaction response bundle."""
    ids = []
    for entry in response_bundle.get("entry", []):
        location = entry.get("response", {}).get("location", "")
        parts = location.split("/")
        if "Patient" in parts:
            idx = parts.index("Patient")
            if idx + 1 < len(parts):
                ids.append(parts[idx + 1])
    return ids


def _post_bundle(
    base_url: str, token_manager: OAuth2TokenManager, bundle: dict
) -> dict:
    url = _normalise_base_url(base_url)
    with httpx.Client(timeout=30) as client:
        r = client.post(url, headers=_auth_headers(token_manager), json=bundle)
        r.raise_for_status()
        return r.json()


def seed_from_file(config: FHIRAuthConfig, path: Path) -> list[str]:
    """Upload a FHIR JSON file to the server. Returns server-assigned Patient IDs."""
    token_manager = OAuth2TokenManager(config.to_oauth2_config())
    data = json.loads(path.read_text())
    bundle = _as_transaction_bundle(data)
    response = _post_bundle(config.base_url, token_manager, bundle)
    return _patient_ids_from_response(response)


def seed_from_directory(config: FHIRAuthConfig, path: Path) -> dict[str, list[str]]:
    """Upload all *.json files in a directory. Returns {stem: [patient_ids]}."""
    token_manager = OAuth2TokenManager(config.to_oauth2_config())
    results: dict[str, list[str]] = {}
    for json_file in sorted(path.glob("*.json")):
        data = json.loads(json_file.read_text())
        bundle = _as_transaction_bundle(data)
        response = _post_bundle(config.base_url, token_manager, bundle)
        results[json_file.stem] = _patient_ids_from_response(response)
    return results
