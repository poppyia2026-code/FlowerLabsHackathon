"""F1 (FLOWER-11): typed claim schema + synthetic happy/escalate fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from poppy_orchestrator.clients.hospital_cred import StubHospitalCredClient
from poppy_orchestrator.clients.payer_enrollment import StubPayerEnrollmentClient
from poppy_orchestrator.contracts.claims import (
    F1_CORE_CLAIMS,
    HOSPITAL_CRED_CLAIMS,
    PAYER_ENROLLMENT_CLAIMS,
    ClaimRequest,
    ClaimType,
    ProviderRef,
    new_request_id,
)
from poppy_orchestrator.fixtures.loader import (
    ESCALATE_PROVIDER_ID,
    HAPPY_PROVIDER_ID,
    SUPERNODE_LAYOUT,
    f1_claims_present,
    load_hospital_cred_catalog,
    load_orchestrator_catalog,
    load_payer_enrollment_catalog,
    load_provider_row,
)

ROOT = Path(__file__).resolve().parents[1]
F1_SCHEMA_PATH = ROOT / "schemas" / "f1_claims.schema.json"


@pytest.fixture(scope="module")
def f1_schema() -> dict:
    with F1_SCHEMA_PATH.open() as f:
        return json.load(f)


def _validate_definition(instance: dict, schema: dict, definition: str) -> None:
    resolver_schema = {
        "$schema": schema.get("$schema"),
        "$ref": f"#/definitions/{definition}",
        "definitions": schema["definitions"],
    }
    jsonschema.validate(instance=instance, schema=resolver_schema)


# --- Schema / typed claims ---


def test_f1_core_claim_types_exact():
    assert F1_CORE_CLAIMS == frozenset(
        {
            "license_active",
            "npi_enumerated",
            "exclusion_clear",
            "work_history_complete",
        }
    )
    for name in F1_CORE_CLAIMS:
        assert name in {c.value for c in ClaimType}


def test_f1_claim_type_enum_validates(f1_schema):
    for name in F1_CORE_CLAIMS:
        _validate_definition(name, f1_schema, "f1_claim_type")


def test_f1_schema_rejects_unknown_claim_type(f1_schema):
    with pytest.raises(jsonschema.ValidationError):
        _validate_definition("hipaa_certified", f1_schema, "f1_claim_type")


# --- Fixture catalogs ---


def test_orchestrator_catalog_validates(f1_schema):
    catalog = load_orchestrator_catalog()
    _validate_definition(catalog, f1_schema, "providers_catalog")
    assert catalog["meta"]["synthetic"] is True


def test_hospital_supernode_catalog_validates(f1_schema):
    catalog = load_hospital_cred_catalog()
    _validate_definition(catalog, f1_schema, "hospital_node_catalog")
    assert catalog["meta"]["node"] == "HospitalCred"
    assert SUPERNODE_LAYOUT["HospitalCred"].is_file()


def test_payer_supernode_catalog_validates(f1_schema):
    catalog = load_payer_enrollment_catalog()
    _validate_definition(catalog, f1_schema, "payer_node_catalog")
    assert catalog["meta"]["node"] == "PayerEnrollment"
    assert SUPERNODE_LAYOUT["PayerEnrollment"].is_file()


def test_happy_path_fixture_has_all_f1_claims():
    row = load_provider_row(HAPPY_PROVIDER_ID)
    assert row["path"] == "happy"
    assert f1_claims_present(row) == set(F1_CORE_CLAIMS)
    assert row["hospital_cred"]["work_history_complete"]["value"] is True
    assert row["payer_enrollment"]["license_active"]["value"] is True
    assert row["payer_enrollment"]["npi_enumerated"]["value"] is True
    assert row["payer_enrollment"]["exclusion_clear"]["value"] is True


def test_escalate_path_fixture_flags_for_hitl():
    row = load_provider_row(ESCALATE_PROVIDER_ID)
    assert row["path"] == "escalate"
    assert f1_claims_present(row) == set(F1_CORE_CLAIMS)
    assert row["hospital_cred"]["work_history_complete"]["value"] is False
    assert row["payer_enrollment"]["exclusion_clear"]["value"] is False


def test_happy_and_escalate_served_by_stub_clients():
    hospital = StubHospitalCredClient()
    payer = StubPayerEnrollmentClient()
    provider = ProviderRef(
        provider_id=HAPPY_PROVIDER_ID,
        network_id="SYNTH-NETWORK-X",
        display_name="Synthetic Provider P (happy path)",
    )

    hosp = hospital.request_claims(
        ClaimRequest(
            request_id=new_request_id("hosp"),
            provider=provider,
            claim_types=tuple(sorted(HOSPITAL_CRED_CLAIMS)),
            source_node="HospitalCred",
        )
    )
    pay = payer.request_claims(
        ClaimRequest(
            request_id=new_request_id("pay"),
            provider=provider,
            claim_types=tuple(sorted(PAYER_ENROLLMENT_CLAIMS)),
            source_node="PayerEnrollment",
        )
    )
    assert hosp.ok and pay.ok
    types = {c.claim_type for c in (*hosp.claims, *pay.claims)}
    assert F1_CORE_CLAIMS.issubset(types)

    escalate = ProviderRef(
        provider_id=ESCALATE_PROVIDER_ID,
        network_id="SYNTH-NETWORK-X",
    )
    hosp_q = hospital.request_claims(
        ClaimRequest(
            request_id=new_request_id("hosp"),
            provider=escalate,
            claim_types=("work_history_complete",),
            source_node="HospitalCred",
        )
    )
    pay_q = payer.request_claims(
        ClaimRequest(
            request_id=new_request_id("pay"),
            provider=escalate,
            claim_types=("exclusion_clear",),
            source_node="PayerEnrollment",
        )
    )
    assert hosp_q.get("work_history_complete").value is False
    assert pay_q.get("exclusion_clear").value is False


def test_no_live_source_markers_in_fixtures():
    """Banned: live CAQH/NPDB pulls or HIPAA-certified / HITRUST-as-ours claims."""
    blobs = [
        load_orchestrator_catalog(),
        load_hospital_cred_catalog(),
        load_payer_enrollment_catalog(),
    ]
    banned = ("caqh.com", "npdb.hrsa", "hipaa-certified", "hitrust-certified", "75% faster")
    raw = json.dumps(blobs).lower()
    for token in banned:
        assert token not in raw
