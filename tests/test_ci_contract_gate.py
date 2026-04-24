from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import Mock

import pytest

from healthchain.config.appconfig import AppConfig
from healthchain.fhir import create_document_reference
from healthchain.io.adapters.cdaadapter import CdaAdapter
from healthchain.io.adapters.cdsfhiradapter import CdsFhirAdapter
from healthchain.io.containers import Document
from healthchain.interop import FormatType
from healthchain.models.requests.cdarequest import CdaRequest

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "healthchain"
LAYER4_PREFIXES = ("healthchain/cli.py", "healthchain/sandbox/")
LAYER1_PREFIXES = ("healthchain/io/containers/",)
LAYER1_FILES = {"healthchain/io/types.py", "healthchain/pipeline/base.py"}
LAYER3_PREFIXES = ("healthchain/interop/",)
HTTP_TRANSPORT_PREFIXES = (
    "fastapi",
    "starlette",
    "httpx",
    "requests",
    "uvicorn",
    "fastapi_events",
)
ALLOWLISTED_IMPORT_PREFIXES = {
    "healthchain/gateway/cds/__init__.py": ("healthchain.sandbox",),
}


def _module_name_for_path(path: Path) -> str:
    relative = path.relative_to(REPO_ROOT).with_suffix("")
    return ".".join(relative.parts)


def _resolve_from_import(module_name: str, level: int, imported_module: str) -> str:
    package_parts = module_name.split(".")[:-1]
    if level:
        package_parts = package_parts[: len(package_parts) - level + 1]
    if imported_module:
        package_parts.extend(imported_module.split("."))
    return ".".join(part for part in package_parts if part)


def _iter_import_targets(path: Path) -> set[str]:
    module_name = _module_name_for_path(path)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
            continue
        if not isinstance(node, ast.ImportFrom):
            continue

        base_module = _resolve_from_import(module_name, node.level, node.module or "")
        if base_module:
            imports.add(base_module)

        for alias in node.names:
            if alias.name == "*":
                continue
            if base_module:
                imports.add(f"{base_module}.{alias.name}")
            elif node.module:
                imports.add(f"{node.module}.{alias.name}")

    return imports


def _is_layer4(relative_path: str) -> bool:
    return relative_path == "healthchain/cli.py" or relative_path.startswith(
        "healthchain/sandbox/"
    )


def _is_layer1(relative_path: str) -> bool:
    return relative_path in LAYER1_FILES or relative_path.startswith(LAYER1_PREFIXES)


def _is_layer3(relative_path: str) -> bool:
    return relative_path.startswith(LAYER3_PREFIXES)


def _is_allowlisted(relative_path: str, imported_module: str) -> bool:
    allowed_prefixes = ALLOWLISTED_IMPORT_PREFIXES.get(relative_path, ())
    return any(imported_module.startswith(prefix) for prefix in allowed_prefixes)


def test_reviewed_architecture_boundaries_remain_narrow() -> None:
    violations: list[str] = []

    for path in PACKAGE_ROOT.rglob("*.py"):
        relative_path = path.relative_to(REPO_ROOT).as_posix()
        if _is_layer4(relative_path):
            continue

        for imported_module in sorted(_iter_import_targets(path)):
            if _is_allowlisted(relative_path, imported_module):
                continue

            if imported_module.startswith(("healthchain.cli", "healthchain.sandbox")):
                violations.append(
                    f"{relative_path} imports tooling concern {imported_module}"
                )

            if _is_layer1(relative_path) and imported_module.startswith(
                "healthchain.gateway"
            ):
                violations.append(
                    f"{relative_path} imports runtime shell concern {imported_module}"
                )

            if _is_layer3(relative_path) and imported_module.startswith(
                HTTP_TRANSPORT_PREFIXES
            ):
                violations.append(
                    f"{relative_path} imports HTTP transport concern {imported_module}"
                )

    assert violations == []


def test_document_contract_smoke() -> None:
    document = Document(data="Patient has hypertension")

    assert document.input == "Patient has hypertension"
    assert document.text == "Patient has hypertension"

    document.set_metadata("source", "ci-gate")
    document.add_artifact("normalized-note", {"ok": True}, version="v1")
    document.execution.mark_stage("parse", adapter="smoke")

    assert document.metadata["source"] == "ci-gate"
    assert document.artifacts["normalized-note"]["version"] == "v1"
    assert document.execution["stage"] == "parse"
    assert document.execution["adapter"] == "smoke"

    document.clear_execution()

    assert document.execution.as_dict() == {}
    assert document.metadata["source"] == "ci-gate"


def test_appconfig_startup_validation_smoke(tmp_path: Path) -> None:
    valid_path = tmp_path / "healthchain-valid.yaml"
    valid_path.write_text("name: ci-gate\n", encoding="utf-8")
    config, summary = AppConfig.load_with_summary(valid_path, strict=True)
    assert config is not None
    assert summary.status == "valid"

    defaulted_path = tmp_path / "healthchain-missing.yaml"
    missing_config, missing_summary = AppConfig.load_with_summary(defaulted_path)
    assert missing_config is None
    assert missing_summary.status == "defaulted"

    invalid_path = tmp_path / "healthchain-invalid.yaml"
    invalid_path.write_text("security:\n  auth: magic-token\n", encoding="utf-8")
    config, summary = AppConfig.load_with_summary(invalid_path)
    assert config is None
    assert summary.status == "invalid"
    assert summary.errors

    with pytest.raises(ValueError):
        AppConfig.load_with_summary(invalid_path, strict=True)


def test_cds_fhir_adapter_contract_smoke(
    test_cds_request, doc_ref_with_content
) -> None:
    adapter = CdsFhirAdapter()
    test_cds_request.prefetch["document"] = doc_ref_with_content.model_dump(
        exclude_none=True
    )

    document = adapter.parse(test_cds_request)

    assert document.input == "Test document content"
    assert document.fhir.prefetch_resources["document"].id == doc_ref_with_content.id


def test_cda_adapter_contract_smoke(
    test_condition, test_medication, test_allergy
) -> None:
    engine = Mock()
    note_reference = create_document_reference(
        data="Extracted SOAP note",
        content_type="text/plain",
        description="Converted note",
    )
    engine.to_fhir.return_value = [
        test_condition,
        test_medication,
        test_allergy,
        note_reference,
    ]

    adapter = CdaAdapter(engine=engine)
    document = adapter.parse(CdaRequest(document="<xml>Test CDA</xml>"))

    engine.to_fhir.assert_called_once_with(
        "<xml>Test CDA</xml>", src_format=FormatType.CDA
    )
    assert document.input == "Extracted SOAP note"
    assert len(document.fhir.problem_list) == 1
    assert len(document.fhir.medication_list) == 1
    assert len(document.fhir.allergy_list) == 1
    assert len(document.fhir.get_resources("DocumentReference")) == 2
