"""The dispute and follow-up fields stay inside the published contract."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from poppy_orchestrator.clients.hospital_cred import StubHospitalCredClient
from poppy_orchestrator.clients.payer_enrollment import StubPayerEnrollmentClient
from poppy_orchestrator.contracts.claims import (
    ClaimRequest,
    ProviderRef,
    claim_response_from_dict,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas/claim_contract.schema.json").read_text())
EXPLAINED = "SYNTH-NPI-1777777777"
CLAIM = "work_history_complete"


def check(instance: dict, definition: str) -> None:
    jsonschema.validate(
        instance=instance,
        schema={"$ref": f"#/definitions/{definition}", "definitions": SCHEMA["definitions"]},
    )


def payer_response():
    request = ClaimRequest(
        request_id="pay-1",
        provider=ProviderRef(EXPLAINED, "SYNTH-NETWORK-X"),
        claim_types=("license_active",),
        source_node="PayerEnrollment",
    )
    return StubPayerEnrollmentClient().request_claims(request)


def recheck_request() -> ClaimRequest:
    return ClaimRequest(
        request_id="recheck-1",
        provider=ProviderRef(EXPLAINED, "SYNTH-NETWORK-X"),
        claim_types=(CLAIM,),
        source_node="HospitalCred",
        recheck=payer_response().disputes[0],
    )


def test_response_with_a_dispute_matches_the_contract() -> None:
    check(payer_response().to_dict(), "claim_response")


def test_recheck_request_matches_the_contract() -> None:
    check(recheck_request().to_dict(), "claim_request")


def test_follow_up_answer_matches_the_contract() -> None:
    response = StubHospitalCredClient().request_claims(recheck_request())

    check(response.to_dict(), "claim_response")
    assert response.claims[0].resolves_dispute is True


def test_dispute_survives_the_trip_over_the_grid() -> None:
    sent = payer_response()

    received = claim_response_from_dict(json.loads(json.dumps(sent.to_dict())))

    assert received.disputes == sent.disputes


def test_unknown_fields_are_still_rejected() -> None:
    instance = {**payer_response().to_dict(), "dossier": "raw file"}

    with pytest.raises(jsonschema.ValidationError):
        check(instance, "claim_response")


def test_receipt_records_the_dispute(monkeypatch) -> None:
    from poppy_orchestrator.agent_app import kickoff_credentialing
    from poppy_orchestrator.events.emit import LocalEventBus
    from poppy_orchestrator.hitl.pause import AutoApproveHitlGate

    monkeypatch.setenv("ENDEAVOR_ENABLED", "0")
    result = kickoff_credentialing(
        provider_id=EXPLAINED, emitter=LocalEventBus(), hitl_gate=AutoApproveHitlGate()
    )

    assert "Dispute on work_history_complete" in result.receipt.message
    assert "explained" in result.receipt.message
    check(result.receipt.to_dict(), "claim_receipt")
