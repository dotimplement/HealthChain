"""Smoke tests to verify cookbook examples import without errors.

Run locally after making changes to HealthChainAPI or gateway interfaces.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

COOKBOOK_DIR = Path(__file__).parents[2] / "cookbook"

COOKBOOKS = [
    "cds_discharge_summarizer_hf_chat",
    "cds_discharge_summarizer_hf_trf",
    "fhir_context_llm_qa",
    "multi_ehr_data_aggregation",
    "notereader_clinical_coding_fhir",
    "sepsis_cds_hooks",
    "sepsis_fhir_batch",
]


@pytest.mark.skip(reason="local only")
@pytest.mark.parametrize("name", COOKBOOKS)
def test_cookbook_imports(name):
    path = COOKBOOK_DIR / f"{name}.py"
    assert path.exists(), f"Cookbook file not found: {path}"

    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
