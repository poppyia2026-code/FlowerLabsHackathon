"""F6 acceptance: claim contract + mandatory HITL gate.

AC (docs/BOARD.md):
  Shared request/response; fail if node missing; never skip HITL; scripted fixture test.
"""

from __future__ import annotations

from typing import Optional
from pathlib import Path

import jsonschema
import pytest

from poppy_orchestrator.clients.base import SuperNodeClaimClient
from poppy_orchestrator.clients.hospital_cred import StubHospitalCredClient
from poppy_orchestrator.clients.payer_enrollment import StubPayerEnrollmentClient
from poppy_orchestrator.contracts.claims import (
    HOSPITAL_CRED_CLAIMS,
    PAYER_ENROLLMENT_CLAIMS,
    ClaimRequest,
    ClaimResponse,
    CredentialingOutcome,
    HitlAction,
    HitlDecision,
    ProviderRef,
    new_request_id,
)
from poppy_orchestrator.events.emit import LocalEventBus, NullEmitter
from poppy_orchestrator.hitl.pause import CallbackHitlGate, HitlGate
from poppy_orchestrator.orchestration.flow import OrchestratorConfig, run_credentialing_flow

ROOT = Path(__file__).resolve().parents[1]


class RecordingHitlGate(HitlGate):
    """Records whether wait_for_decision was invoked (HITL must not be skipped)."""

    def __init__(self, action: HitlAction = HitlAction.APPROVE) -> None:
        self.action = action
        self.calls = 0
        self.last_bundle = None

    def wait_for_decision(self, bundle, emitter, *, timeout_s: Optional[float] = None) -> HitlDecision:
        self.calls += 1
        self.last_bundle = bundle
        emitter.emit(
            {
                "event": "privcred.hitl.request",
                "data": {"bundle": bundle.to_dict(), "synthetic": True},
            }
        )
        decision = HitlDecision(
            action=self.action,
            actor="test-hitl",
            reason="recording-gate",
        )
        emitter.emit({"event": "privcred.hitl.decision", "data": decision.to_dict()})
        return decision


class MissingNodeClient(SuperNodeClaimClient):
    """Simulates an unavailable SuperNode (ok=false)."""

    def __init__(self, node_name: str) -> None:
        self.node_name = node_name

    def request_claims(self, request: ClaimRequest) -> ClaimResponse:
        return ClaimResponse(
            request_id=request.request_id,
            source_node=self.node_name,
            provider_id=request.provider.provider_id,
            claims=(),
            ok=False,
            error=f"{self.node_name} unavailable (synthetic missing-node fixture)",
            synthetic=True,
        )


def _validate_definition(instance: dict, schema: dict, definition: str) -> None:
    resolver_schema = {
        "$schema": schema.get("$schema"),
        "$ref": f"#/definitions/{definition}",
        "definitions": schema["definitions"],
    }
    jsonschema.validate(instance=instance, schema=resolver_schema)


# --- Schema contract ---


def test_claim_request_validates_against_schema(claim_contract_schema):
    provider = ProviderRef(provider_id="SYNTH-NPI-1999999999", network_id="SYNTH-NETWORK-X")
    req = ClaimRequest(
        request_id=new_request_id("hosp"),
        provider=provider,
        claim_types=tuple(sorted(HOSPITAL_CRED_CLAIMS)),
        source_node="HospitalCred",
    )
    _validate_definition(req.to_dict(), claim_contract_schema, "claim_request")


def test_claim_response_validates_against_schema(claim_contract_schema):
    hospital = StubHospitalCredClient()
    provider = ProviderRef(provider_id="SYNTH-NPI-1999999999", network_id="SYNTH-NETWORK-X")
    req = ClaimRequest(
        request_id=new_request_id("hosp"),
        provider=provider,
        claim_types=tuple(sorted(HOSPITAL_CRED_CLAIMS)),
        source_node="HospitalCred",
    )
    resp = hospital.request_claims(req)
    assert resp.ok
    _validate_definition(resp.to_dict(), claim_contract_schema, "claim_response")


def test_payer_claim_response_validates_against_schema(claim_contract_schema):
    payer = StubPayerEnrollmentClient()
    provider = ProviderRef(provider_id="SYNTH-NPI-1999999999", network_id="SYNTH-NETWORK-X")
    req = ClaimRequest(
        request_id=new_request_id("pay"),
        provider=provider,
        claim_types=tuple(sorted(PAYER_ENROLLMENT_CLAIMS)),
        source_node="PayerEnrollment",
    )
    resp = payer.request_claims(req)
    assert resp.ok
    _validate_definition(resp.to_dict(), claim_contract_schema, "claim_response")


def test_happy_path_receipt_validates_against_schema(claim_contract_schema):
    gate = RecordingHitlGate(HitlAction.APPROVE)
    bus = LocalEventBus()
    result = run_credentialing_flow(
        hospital=StubHospitalCredClient(),
        payer=StubPayerEnrollmentClient(),
        hitl_gate=gate,
        emitter=bus,
        config=OrchestratorConfig(provider_id="SYNTH-NPI-1999999999"),
    )
    assert result.receipt is not None
    _validate_definition(result.receipt.to_dict(), claim_contract_schema, "claim_receipt")


def test_schema_rejects_non_synthetic_request(claim_contract_schema):
    bad = {
        "request_id": "req-x",
        "provider": {"provider_id": "SYNTH-NPI-1999999999", "network_id": "SYNTH-NETWORK-X"},
        "claim_types": ["board_status"],
        "source_node": "HospitalCred",
        "synthetic": False,
    }
    with pytest.raises(jsonschema.ValidationError):
        _validate_definition(bad, claim_contract_schema, "claim_request")


# --- HITL cannot be skipped ---


def test_hitl_cannot_be_skipped_happy_path():
    gate = RecordingHitlGate(HitlAction.APPROVE)
    bus = LocalEventBus()
    result = run_credentialing_flow(
        hospital=StubHospitalCredClient(),
        payer=StubPayerEnrollmentClient(),
        hitl_gate=gate,
        emitter=bus,
        config=OrchestratorConfig(provider_id="SYNTH-NPI-1999999999"),
    )
    assert gate.calls == 1, "HITL gate must be invoked exactly once"
    assert result.hitl is not None
    assert result.hitl.action == HitlAction.APPROVE
    assert result.outcome == CredentialingOutcome.CREDENTIALED
    hitl_events = [e for e in bus.events if e.get("event") == "privcred.hitl.request"]
    assert len(hitl_events) >= 1, "privcred.hitl.request must be emitted (HITL pause)"


def test_hitl_still_required_when_node_missing():
    """Missing node must not bypass HITL — gate still runs; outcome fails closed."""
    gate = RecordingHitlGate(HitlAction.APPROVE)
    bus = LocalEventBus()
    result = run_credentialing_flow(
        hospital=MissingNodeClient("HospitalCred"),
        payer=StubPayerEnrollmentClient(),
        hitl_gate=gate,
        emitter=bus,
        config=OrchestratorConfig(provider_id="SYNTH-NPI-1999999999"),
    )
    assert gate.calls == 1, "HITL must not be skipped when a node is missing"
    assert result.hitl is not None
    assert "HospitalCred" in result.bundle.missing_nodes()


def test_callback_gate_is_mandatory_pause():
    called = {"n": 0}

    def wait_fn(bundle_dict, timeout_s):
        called["n"] += 1
        assert "claims" in bundle_dict or "provider" in bundle_dict
        return {"action": "reject", "actor": "test", "reason": "callback-reject"}

    gate = CallbackHitlGate(wait_fn=wait_fn)
    result = run_credentialing_flow(
        hospital=StubHospitalCredClient(),
        payer=StubPayerEnrollmentClient(),
        hitl_gate=gate,
        emitter=NullEmitter(),
        config=OrchestratorConfig(provider_id="SYNTH-NPI-1999999999"),
    )
    assert called["n"] == 1
    assert result.outcome == CredentialingOutcome.REJECTED
    assert result.receipt is None


# --- Missing node fails ---


def test_missing_hospital_node_fails_on_approve():
    gate = RecordingHitlGate(HitlAction.APPROVE)
    result = run_credentialing_flow(
        hospital=MissingNodeClient("HospitalCred"),
        payer=StubPayerEnrollmentClient(),
        hitl_gate=gate,
        emitter=NullEmitter(),
        config=OrchestratorConfig(provider_id="SYNTH-NPI-1999999999"),
    )
    assert result.bundle.missing_nodes() == ["HospitalCred"]
    assert result.outcome == CredentialingOutcome.FAILED
    # Approve still issues a receipt documenting the failed outcome
    assert result.receipt is not None
    assert result.receipt.outcome == CredentialingOutcome.FAILED


def test_missing_payer_node_fails_on_approve():
    gate = RecordingHitlGate(HitlAction.APPROVE)
    result = run_credentialing_flow(
        hospital=StubHospitalCredClient(),
        payer=MissingNodeClient("PayerEnrollment"),
        hitl_gate=gate,
        emitter=NullEmitter(),
        config=OrchestratorConfig(provider_id="SYNTH-NPI-1999999999"),
    )
    assert result.bundle.missing_nodes() == ["PayerEnrollment"]
    assert result.outcome == CredentialingOutcome.FAILED


def test_both_nodes_missing_fails():
    gate = RecordingHitlGate(HitlAction.APPROVE)
    result = run_credentialing_flow(
        hospital=MissingNodeClient("HospitalCred"),
        payer=MissingNodeClient("PayerEnrollment"),
        hitl_gate=gate,
        emitter=NullEmitter(),
        config=OrchestratorConfig(provider_id="SYNTH-NPI-1999999999"),
    )
    assert set(result.bundle.missing_nodes()) == {"HospitalCred", "PayerEnrollment"}
    assert result.outcome == CredentialingOutcome.FAILED


def test_unknown_provider_marks_nodes_missing():
    """Unknown synthetic provider_id → stubs return ok=false → missing nodes → FAILED."""
    gate = RecordingHitlGate(HitlAction.APPROVE)
    result = run_credentialing_flow(
        hospital=StubHospitalCredClient(),
        payer=StubPayerEnrollmentClient(),
        hitl_gate=gate,
        emitter=NullEmitter(),
        config=OrchestratorConfig(provider_id="SYNTH-NPI-0000000000"),
    )
    assert gate.calls == 1
    assert set(result.bundle.missing_nodes()) == {"HospitalCred", "PayerEnrollment"}
    assert result.outcome == CredentialingOutcome.FAILED


def test_escalate_path_does_not_credential_even_with_both_nodes():
    gate = RecordingHitlGate(HitlAction.ESCALATE)
    result = run_credentialing_flow(
        hospital=StubHospitalCredClient(),
        payer=StubPayerEnrollmentClient(),
        hitl_gate=gate,
        emitter=NullEmitter(),
        config=OrchestratorConfig(
            provider_id="SYNTH-NPI-1888888888",
            display_name="Synthetic Provider Q",
        ),
    )
    assert result.outcome == CredentialingOutcome.ESCALATED
    assert result.receipt is None
