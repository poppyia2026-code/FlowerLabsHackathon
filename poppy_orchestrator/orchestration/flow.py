"""PoppyOrchestrator credentialing flow (F5).

Kickoff → HospitalCred claims → PayerEnrollment claims → HITL → receipt.

Failure if a node is missing: flow still reaches HITL (never silent skip)
but outcome cannot be credentialed without Approve + both nodes ok.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import uuid

from poppy_orchestrator.clients.base import SuperNodeClaimClient
from poppy_orchestrator.contracts.claims import (
    HOSPITAL_CRED_CLAIMS,
    PAYER_ENROLLMENT_CLAIMS,
    ClaimBundle,
    ClaimReceipt,
    ClaimRequest,
    ClaimResponse,
    CredentialingOutcome,
    HitlAction,
    HitlDecision,
    ProviderRef,
    new_receipt_id,
    new_request_id,
    validate_claim_response,
)
from poppy_orchestrator.events.emit import EventEmitter, emit_stage, emit_text
from poppy_orchestrator.hitl.pause import HitlGate


@dataclass
class OrchestratorConfig:
    provider_id: str = "SYNTH-NPI-1999999999"
    network_id: str = "SYNTH-NETWORK-X"
    display_name: str = "Synthetic Provider P"
    run_id: Optional[str] = None


@dataclass
class FlowResult:
    run_id: str
    bundle: ClaimBundle
    hitl: Optional[HitlDecision]
    receipt: Optional[ClaimReceipt]
    outcome: CredentialingOutcome


def run_credentialing_flow(
    *,
    hospital: SuperNodeClaimClient,
    payer: SuperNodeClaimClient,
    hitl_gate: HitlGate,
    emitter: EventEmitter,
    config: OrchestratorConfig,
) -> FlowResult:
    run_id = config.run_id or f"run-{uuid.uuid4().hex[:12]}"
    provider = ProviderRef(
        provider_id=config.provider_id,
        network_id=config.network_id,
        display_name=config.display_name,
    )

    emit_stage(emitter, "kickoff", provider.to_dict())
    emit_text(
        emitter,
        f"PrivCred PoppyOrchestrator: credential {provider.display_name} "
        f"({provider.provider_id}) for network {provider.network_id} "
        "[synthetic fixtures only — no live CAQH/NPDB].",
    )

    # --- HospitalCred ---
    hosp_req = ClaimRequest(
        request_id=new_request_id("hosp"),
        provider=provider,
        claim_types=tuple(sorted(HOSPITAL_CRED_CLAIMS)),
        source_node="HospitalCred",
    )
    emit_stage(emitter, "claim_request.HospitalCred", hosp_req.to_dict())
    hosp_resp = hospital.request_claims(hosp_req)
    emit_stage(emitter, "claim_response.HospitalCred", hosp_resp.to_dict())
    hosp_errs = validate_claim_response(
        hosp_resp,
        hosp_req.claim_types,
        allowed_for_node=HOSPITAL_CRED_CLAIMS,
    )
    if hosp_errs:
        emit_text(emitter, f"HospitalCred validation: {hosp_errs}")
        # F6 fail-closed: incomplete/invalid claims must not look like a healthy node
        if hosp_resp.ok:
            hosp_resp = ClaimResponse(
                request_id=hosp_resp.request_id,
                source_node=hosp_resp.source_node,
                provider_id=hosp_resp.provider_id,
                claims=(),
                ok=False,
                error="; ".join(hosp_errs),
                synthetic=hosp_resp.synthetic,
            )

    # --- PayerEnrollment ---
    pay_req = ClaimRequest(
        request_id=new_request_id("pay"),
        provider=provider,
        claim_types=tuple(sorted(PAYER_ENROLLMENT_CLAIMS)),
        source_node="PayerEnrollment",
    )
    emit_stage(emitter, "claim_request.PayerEnrollment", pay_req.to_dict())
    pay_resp = payer.request_claims(pay_req)
    emit_stage(emitter, "claim_response.PayerEnrollment", pay_resp.to_dict())
    pay_errs = validate_claim_response(
        pay_resp,
        pay_req.claim_types,
        allowed_for_node=PAYER_ENROLLMENT_CLAIMS,
    )
    if pay_errs:
        emit_text(emitter, f"PayerEnrollment validation: {pay_errs}")
        # F6 fail-closed: incomplete/invalid claims must not look like a healthy node
        if pay_resp.ok:
            pay_resp = ClaimResponse(
                request_id=pay_resp.request_id,
                source_node=pay_resp.source_node,
                provider_id=pay_resp.provider_id,
                claims=(),
                ok=False,
                error="; ".join(pay_errs),
                synthetic=pay_resp.synthetic,
            )

    bundle = ClaimBundle(
        run_id=run_id,
        provider=provider,
        hospital=hosp_resp,
        payer=pay_resp,
    )
    emit_stage(emitter, "claims_aggregated", bundle.to_dict())

    # --- HITL (mandatory — never silent skip) ---
    hitl = hitl_gate.wait_for_decision(bundle, emitter)
    outcome = _map_outcome(hitl, bundle)

    receipt: Optional[ClaimReceipt] = None
    if hitl.action == HitlAction.APPROVE:
        receipt = ClaimReceipt(
            receipt_id=new_receipt_id(),
            run_id=run_id,
            provider=provider,
            outcome=outcome,
            hitl=hitl,
            claims_snapshot=[c.to_dict() for c in bundle.all_claims()],
            message=(
                "Verification completed under human supervision. "
                "Synthetic demo — not a production credentialing decision."
            ),
        )
        # TODO FRANCO (F8): enrich receipt presentation in UI / Flower Chat
        emitter.emit({"event": "privcred.claim_receipt", "data": receipt.to_dict()})
        emit_text(emitter, f"Claim receipt {receipt.receipt_id}: {receipt.message}")
    elif hitl.action == HitlAction.ESCALATE:
        emit_text(emitter, "Escalated — request more / human follow-up (no receipt).")
    else:
        emit_text(emitter, "Rejected by human — no credentialed status.")

    emit_stage(
        emitter,
        "complete",
        {"outcome": outcome.value, "receipt_id": receipt.receipt_id if receipt else None},
    )
    return FlowResult(
        run_id=run_id,
        bundle=bundle,
        hitl=hitl,
        receipt=receipt,
        outcome=outcome,
    )


def _map_outcome(hitl: HitlDecision, bundle: ClaimBundle) -> CredentialingOutcome:
    if hitl.action == HitlAction.REJECT:
        return CredentialingOutcome.REJECTED
    if hitl.action == HitlAction.ESCALATE:
        return CredentialingOutcome.ESCALATED
    # Approve path: still fail closed if a node was missing
    if bundle.missing_nodes():
        return CredentialingOutcome.FAILED
    return CredentialingOutcome.CREDENTIALED
