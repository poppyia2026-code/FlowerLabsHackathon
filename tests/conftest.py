"""Shared fixtures for PrivCred orchestrator tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "claim_contract.schema.json"
F1_SCHEMA_PATH = ROOT / "schemas" / "f1_claims.schema.json"


@pytest.fixture(scope="session")
def claim_contract_schema() -> dict:
    with SCHEMA_PATH.open() as f:
        return json.load(f)


@pytest.fixture(scope="session")
def schema_path() -> Path:
    return SCHEMA_PATH


@pytest.fixture(scope="session")
def f1_claims_schema() -> dict:
    with F1_SCHEMA_PATH.open() as f:
        return json.load(f)
