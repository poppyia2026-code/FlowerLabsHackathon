"""Emit auditable run-series receipt ONLY after HITL Approve (F8 / FLOWER-13).

Hook from orchestrator pause/approve path. Escalate and Reject must not
produce a credentialed receipt.
"""

from __future__ import annotations

from typing import Any, Optional, Sequence

from poppy_orchestrator.contracts.claims import (
    ClaimBundle,
    ClaimReceipt,
    CredentialingOutcome,
    HitlAction,
    HitlDecision,
    new_receipt_id,
)
from poppy_orchestrator.events.emit import EventEmitter, emit_stage, emit_text
from poppy_orchestrator.receipts.format import format_receipt_text

# Default run-series labels (keep aligned with orchestration.flow.FLOW_STAGES)
DEFAULT_RUN_SERIES: tuple[str, ...] = (
    "kickoff",
    "claim_request.HospitalCred",
    "claim_response.HospitalCred",
    "claim_request.PayerEnrollment",
    "claim_response.PayerEnrollment",
    "claims_aggregated",
    "hitl_pause",
    "claim_receipt",
    "complete",
)


APPROVE_ONLY_MESSAGE = (
    "Verification completed under human supervision. "
    "Synthetic demo — not a production credentialing decision. "
    "Not a HITRUST or HIPAA-certified audit packet."
)


def maybe_build_approve_receipt(
    *,
    run_id: str,
    bundle: ClaimBundle,
    hitl: HitlDecision,
    outcome: CredentialingOutcome,
    run_series: Optional[Sequence[str]] = None,
) -> Optional[ClaimReceipt]:
    """Build ClaimReceipt only when HITL action is Approve; else None."""
    if hitl.action != HitlAction.APPROVE:
        return None
    receipt = ClaimReceipt(
        receipt_id=new_receipt_id(),
        run_id=run_id,
        provider=bundle.provider,
        outcome=outcome,
        hitl=hitl,
        claims_snapshot=[c.to_dict() for c in bundle.all_claims()],
        message=APPROVE_ONLY_MESSAGE,
    )
    # Attach run-series for audit trail (extra field via to_dict enrichment)
    return receipt


def enrich_receipt_dict(
    receipt: ClaimReceipt,
    *,
    run_series: Optional[Sequence[str]] = None,
) -> dict[str, Any]:
    """Receipt dict + run-series stages for screenshotable audit trail."""
    data = receipt.to_dict()
    data["run_series"] = list(run_series) if run_series is not None else list(DEFAULT_RUN_SERIES)
    data["audit"] = {
        "emitted_after": "hitl_approve",
        "hitl_required": True,
        "synthetic": True,
        "compliance_claims": None,  # explicit: we do not claim HITRUST/HIPAA-cert
    }
    return data


def emit_receipt_after_approve(
    *,
    run_id: str,
    bundle: ClaimBundle,
    hitl: HitlDecision,
    outcome: CredentialingOutcome,
    emitter: EventEmitter,
    run_series: Optional[Sequence[str]] = None,
) -> Optional[ClaimReceipt]:
    """Orchestrator hook: emit receipt events only on Approve.

    Returns the ClaimReceipt when emitted, else None (escalate/reject).
    """
    receipt = maybe_build_approve_receipt(
        run_id=run_id,
        bundle=bundle,
        hitl=hitl,
        outcome=outcome,
        run_series=run_series,
    )
    if receipt is None:
        if hitl.action == HitlAction.ESCALATE:
            emit_text(
                emitter,
                "Escalated — request more / human follow-up (no claim receipt).",
            )
        elif hitl.action == HitlAction.REJECT:
            emit_text(emitter, "Rejected by human — no credentialed receipt.")
        else:
            emit_text(emitter, f"HITL action={hitl.action.value} — no claim receipt.")
        return None

    payload = enrich_receipt_dict(receipt, run_series=run_series)
    emit_stage(emitter, "claim_receipt", payload)
    emitter.emit({"event": "privcred.claim_receipt", "data": payload})
    # Screenshotable text block for Flower Chat / deck / fail-soft
    text_block = format_receipt_text(payload)
    emit_text(emitter, text_block)
    emit_text(emitter, f"Claim receipt {receipt.receipt_id}: {receipt.message}")
    return receipt
