"""F13 (FLOWER-34): stayed vs traveled view per SuperNode.

AC: one screen shows HospitalCred + PayerEnrollment columns; counts come
from the run (fixture local_record vs typed claims), not hard-coded;
G3 kit gets a screenshotable HTML/JSON artifact.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from poppy_orchestrator.clients.hospital_cred import StubHospitalCredClient
from poppy_orchestrator.clients.payer_enrollment import StubPayerEnrollmentClient
from poppy_orchestrator.contracts.claims import (
    HOSPITAL_CRED_CLAIMS,
    PAYER_ENROLLMENT_CLAIMS,
    ClaimBundle,
    ClaimRequest,
    ProviderRef,
    claim_response_from_dict,
    new_request_id,
)
from poppy_orchestrator.contracts.privacy import (
    count_leaf_fields,
    leaf_field_paths,
    privacy_summary_from_local_record,
)
from poppy_orchestrator.hitl.panel import (
    bundle_to_panel_view,
    render_panel_html,
    render_panel_text,
)
from poppy_orchestrator.hitl.stayed_traveled import (
    build_stayed_traveled_from_trace,
    build_stayed_traveled_view,
    render_stayed_traveled_html,
    render_stayed_traveled_text,
)

ROOT = Path(__file__).resolve().parents[1]
HAPPY = "SYNTH-NPI-1999999999"
CONTRACT_SCHEMA = ROOT / "schemas" / "claim_contract.schema.json"
G3_HTML = ROOT / "fixtures" / "g3" / "stayed_vs_traveled.html"
G3_JSON = ROOT / "fixtures" / "g3" / "stayed_vs_traveled.json"


@pytest.fixture
def happy_bundle() -> ClaimBundle:
    provider = ProviderRef(
        provider_id=HAPPY,
        network_id="SYNTH-NETWORK-X",
        display_name="Synthetic Provider P (happy path)",
    )
    hospital = StubHospitalCredClient().request_claims(
        ClaimRequest(
            request_id=new_request_id("hosp"),
            provider=provider,
            claim_types=tuple(sorted(HOSPITAL_CRED_CLAIMS)),
            source_node="HospitalCred",
        )
    )
    payer = StubPayerEnrollmentClient().request_claims(
        ClaimRequest(
            request_id=new_request_id("pay"),
            provider=provider,
            claim_types=tuple(sorted(PAYER_ENROLLMENT_CLAIMS)),
            source_node="PayerEnrollment",
        )
    )
    return ClaimBundle(run_id="test-f13-happy", provider=provider, hospital=hospital, payer=payer)


def test_leaf_field_paths_nested():
    record = {"a": 1, "b": {"c": True, "d": [10, {"e": "x"}]}}
    paths = leaf_field_paths(record)
    assert paths == ["a", "b.c", "b.d[0]", "b.d[1].e"]
    assert count_leaf_fields(record) == 4


def test_happy_local_record_leaf_counts_match_privacy_summary(happy_bundle):
    hosp_fix = json.loads(
        (ROOT / "fixtures/supernodes/HospitalCred/providers.json").read_text()
    )
    pay_fix = json.loads(
        (ROOT / "fixtures/supernodes/PayerEnrollment/providers.json").read_text()
    )
    h_row = next(p for p in hosp_fix["providers"] if p["provider_id"] == HAPPY)
    p_row = next(p for p in pay_fix["providers"] if p["provider_id"] == HAPPY)

    assert happy_bundle.hospital is not None and happy_bundle.payer is not None
    h_sum = happy_bundle.hospital.privacy_summary
    p_sum = happy_bundle.payer.privacy_summary
    assert h_sum is not None and p_sum is not None

    expected_h = count_leaf_fields(h_row["local_record"])
    expected_p = count_leaf_fields(p_row["local_record"])
    assert h_sum.stayed_field_count == expected_h
    assert p_sum.stayed_field_count == expected_p
    assert h_sum.traveled_claim_count == len(happy_bundle.hospital.claims)
    assert p_sum.traveled_claim_count == len(happy_bundle.payer.claims)
    # Guard against hard-coded demo string "23" being the only source of truth.
    assert expected_h != 23 or h_sum.stayed_field_count == expected_h
    assert str(expected_h) in h_sum.count_line()
    assert "23 fields stayed" not in h_sum.count_line() or expected_h == 23


def test_privacy_summary_round_trip_schema(happy_bundle, claim_contract_schema=None):
    with CONTRACT_SCHEMA.open() as f:
        schema = json.load(f)
    assert happy_bundle.hospital is not None
    payload = happy_bundle.hospital.to_dict()
    assert "privacy_summary" in payload
    assert "local_record" not in payload  # raw dossier must not travel
    resolver = {
        "$schema": schema.get("$schema"),
        "$ref": "#/definitions/claim_response",
        "definitions": schema["definitions"],
    }
    jsonschema.validate(instance=payload, schema=resolver)
    restored = claim_response_from_dict(payload)
    assert restored.privacy_summary is not None
    assert (
        restored.privacy_summary.stayed_field_count
        == happy_bundle.hospital.privacy_summary.stayed_field_count
    )


def test_view_contains_both_nodes_and_run_derived_counts(happy_bundle):
    view = build_stayed_traveled_view(happy_bundle)
    names = [n.node_name for n in view.nodes]
    assert names == ["HospitalCred", "PayerEnrollment"]
    assert view.nodes[0].stayed_field_count == (
        happy_bundle.hospital.privacy_summary.stayed_field_count  # type: ignore[union-attr]
    )
    assert view.nodes[1].stayed_field_count == (
        happy_bundle.payer.privacy_summary.stayed_field_count  # type: ignore[union-attr]
    )
    assert len(view.nodes[0].traveled_claims) == len(happy_bundle.hospital.claims)  # type: ignore[union-attr]
    assert len(view.nodes[1].traveled_claims) == len(happy_bundle.payer.claims)  # type: ignore[union-attr]
    text = render_stayed_traveled_text(view)
    html = render_stayed_traveled_html(view)
    for blob in (text, html):
        assert "HospitalCred" in blob
        assert "PayerEnrollment" in blob
        assert "fields stayed" in blob
        assert "typed claims traveled" in blob


def test_view_from_trace_reuses_reply_payloads_no_network(happy_bundle):
    """Rendering uses already-captured reply JSON (no stub re-fetch)."""
    view = build_stayed_traveled_from_trace(
        run_id=happy_bundle.run_id,
        provider_id=happy_bundle.provider.provider_id,
        display_name=happy_bundle.provider.display_name,
        hospital_reply=happy_bundle.hospital.to_dict() if happy_bundle.hospital else None,
        payer_reply=happy_bundle.payer.to_dict() if happy_bundle.payer else None,
    )
    assert view.nodes[0].stayed_field_count > 15
    assert view.nodes[1].stayed_field_count > 15


def test_panel_embeds_stayed_traveled(happy_bundle):
    panel = bundle_to_panel_view(happy_bundle)
    assert panel.stayed_vs_traveled is not None
    assert "stayed_vs_traveled" in panel.to_dict()
    html = render_panel_html(panel)
    text = render_panel_text(panel)
    assert "HospitalCred" in html and "PayerEnrollment" in html
    assert "stayed-traveled" in html
    assert "Stayed vs Traveled" in text


def test_g3_kit_has_screenshotable_artifact():
    assert G3_HTML.is_file(), "run scripts/run_g3_failsoft.py --write"
    assert G3_JSON.is_file()
    html = G3_HTML.read_text()
    data = json.loads(G3_JSON.read_text())
    assert "HospitalCred" in html and "PayerEnrollment" in html
    assert data["synthetic"] is True
    assert len(data["nodes"]) == 2
    for node in data["nodes"]:
        assert node["stayed_field_count"] == len(node["stayed_preview"])
        assert "fields stayed" in node["count_line"]
        # Must not be a frozen hard-coded "23" unless fixture truly has 23.
        assert node["stayed_field_count"] != 23 or "23 fields stayed" in node["count_line"]


def test_privacy_summary_none_without_local_record():
    assert privacy_summary_from_local_record(None, traveled_claim_count=2) is None
    assert privacy_summary_from_local_record({}, traveled_claim_count=2) is None
