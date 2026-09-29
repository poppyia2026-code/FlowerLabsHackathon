"""F8 (FLOWER-13): auditable receipt only after HITL Approve."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import jsonschema
import pytest

from poppy_orchestrator.clients.hospital_cred import StubHospitalCredClient
from poppy_orchestrator.clients.payer_enrollment import StubPayerEnrollmentClient
from poppy_orchestrator.contracts.claims import (
    CredentialingOutcome,
    HitlAction,
    HitlDecision,
)
from poppy_orchestrator.events.emit import LocalEventBus, NullEmitter
from poppy_orchestrator.hitl.pause import HitlGate
from poppy_orchestrator.orchestration.flow import OrchestratorConfig, run_credentialing_flow
from poppy_orchestrator.receipts.emit import (
    emit_receipt_after_approve,
    enrich_receipt_dict,
    maybe_build_approve_receipt,
)
from poppy_orchestrator.receipts.format import format_receipt_json, format_receipt_text

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "claim_contract.schema.json"
EXAMPLE_JSON = ROOT / "fixtures" / "receipts" / "example_approve.json"
EXAMPLE_TXT = ROOT / "fixtures" / "receipts" / "example_approve.txt"


class FixedHitlGate(HitlGate):
    def __init__(self, action: HitlAction) -> None:
        self.action = action

    def wait_for_decision(self, bundle, emitter, *, timeout_s: Optional[float] = None) -> HitlDecision:
        decision = HitlDecision(
            action=self.action,
            actor="f8-test",
            reason=f"test:{self.action.value}",
        )
        emitter.emit({"event": "privcred.hitl.request", "data": {"bundle": bundle.to_dict()}})
        emitter.emit({"event": "privcred.hitl.decision", "data": decision.to_dict()})
        return decision


def _run(action: HitlAction, provider_id: str = "SYNTH-NPI-1999999999"):
    bus = LocalEventBus()
    result = run_credentialing_flow(
        hospital=StubHospitalCredClient(),
        payer=StubPayerEnrollmentClient(),
        hitl_gate=FixedHitlGate(action),
        emitter=bus,
        config=OrchestratorConfig(provider_id=provider_id),
    )
    return result, bus


def test_approve_emits_receipt_and_event():
    result, bus = _run(HitlAction.APPROVE)
    assert result.outcome == CredentialingOutcome.CREDENTIALED
    assert result.receipt is not None
    assert result.receipt.hitl.action == HitlAction.APPROVE
    assert result.receipt.synthetic is True

    receipt_events = [e for e in bus.events if e.get("event") == "privcred.claim_receipt"]
    assert len(receipt_events) == 1
    data = receipt_events[0]["data"]
    assert data["receipt_id"] == result.receipt.receipt_id
    assert "run_series" in data
    assert "hitl_pause" in data["run_series"]
    assert data["audit"]["emitted_after"] == "hitl_approve"

    stages = [
        e["data"]["stage"]
        for e in bus.events
        if e.get("event") == "privcred.stage"
    ]
    assert "claim_receipt" in stages
    assert "hitl_pause" in stages


def test_escalate_no_receipt():
    result, bus = _run(HitlAction.ESCALATE, provider_id="SYNTH-NPI-1888888888")
    assert result.outcome == CredentialingOutcome.ESCALATED
    assert result.receipt is None
    assert not any(e.get("event") == "privcred.claim_receipt" for e in bus.events)
    stages = [
        e["data"]["stage"]
        for e in bus.events
        if e.get("event") == "privcred.stage"
    ]
    assert "claim_receipt" not in stages
    assert "hitl_pause" in stages


def test_reject_no_receipt():
    result, bus = _run(HitlAction.REJECT)
    assert result.outcome == CredentialingOutcome.REJECTED
    assert result.receipt is None
    assert not any(e.get("event") == "privcred.claim_receipt" for e in bus.events)
    stages = [
        e["data"]["stage"]
        for e in bus.events
        if e.get("event") == "privcred.stage"
    ]
    assert "claim_receipt" not in stages


def test_maybe_build_only_on_approve():
    result, _ = _run(HitlAction.APPROVE)
    assert result.hitl is not None
    built = maybe_build_approve_receipt(
        run_id=result.run_id,
        bundle=result.bundle,
        hitl=result.hitl,
        outcome=result.outcome,
    )
    assert built is not None

    escalate_hitl = HitlDecision(action=HitlAction.ESCALATE, actor="x", reason="no")
    assert (
        maybe_build_approve_receipt(
            run_id=result.run_id,
            bundle=result.bundle,
            hitl=escalate_hitl,
            outcome=CredentialingOutcome.ESCALATED,
        )
        is None
    )


def test_screenshotable_text_and_json():
    result, _ = _run(HitlAction.APPROVE)
    assert result.receipt is not None
    payload = enrich_receipt_dict(result.receipt)
    text = format_receipt_text(payload)
    js = format_receipt_json(payload)
    assert "AUDITABLE CLAIM RECEIPT" in text
    assert result.receipt.receipt_id in text
    assert "synthetic" in text.lower()
    assert "HITRUST" in text  # disclaimer that we are NOT claiming it
    parsed = json.loads(js)
    assert parsed["receipt_id"] == result.receipt.receipt_id
    assert parsed["synthetic"] is True


def test_receipt_validates_against_claim_contract_schema():
    with SCHEMA_PATH.open() as f:
        schema = json.load(f)
    result, _ = _run(HitlAction.APPROVE)
    assert result.receipt is not None
    # Schema definition does not include run_series extras — validate core receipt fields
    core = result.receipt.to_dict()
    resolver = {
        "$schema": schema.get("$schema"),
        "$ref": "#/definitions/claim_receipt",
        "definitions": schema["definitions"],
    }
    jsonschema.validate(instance=core, schema=resolver)


def test_example_failsoft_artifacts_exist_and_parse():
    assert EXAMPLE_JSON.is_file(), "fixtures/receipts/example_approve.json missing"
    assert EXAMPLE_TXT.is_file(), "fixtures/receipts/example_approve.txt missing"
    data = json.loads(EXAMPLE_JSON.read_text(encoding="utf-8"))
    assert data["synthetic"] is True
    assert data["hitl"]["action"] == "approve"
    assert "AUDITABLE CLAIM RECEIPT" in EXAMPLE_TXT.read_text(encoding="utf-8")


def test_emit_hook_null_on_reject_with_null_emitter():
    result, _ = _run(HitlAction.APPROVE)
    reject = HitlDecision(action=HitlAction.REJECT, actor="f8", reason="no")
    out = emit_receipt_after_approve(
        run_id=result.run_id,
        bundle=result.bundle,
        hitl=reject,
        outcome=CredentialingOutcome.REJECTED,
        emitter=NullEmitter(),
    )
    assert out is None
