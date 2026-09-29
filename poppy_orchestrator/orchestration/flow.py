"""PoppyOrchestrator credentialing flow (F5).

Kickoff credential P for network X → HospitalCred claims → PayerEnrollment
claims → HITL pause → claim receipt.

Failure if a node is missing: flow still reaches HITL (never silent skip)
but outcome cannot be credentialed without Approve + both nodes ok.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional
import json
import os
import uuid

from poppy_orchestrator.clients.base import SuperNodeClaimClient
from poppy_orchestrator.contracts.claims import (
    HOSPITAL_CRED_CLAIMS,
    PAYER_ENROLLMENT_CLAIMS,
    ClaimBundle,
    ClaimConflict,
    ClaimReceipt,
    ClaimRequest,
    ClaimResponse,
    CredentialingOutcome,
    HitlAction,
    HitlDecision,
    ProviderRef,
    new_request_id,
    validate_claim_response,
)
from poppy_orchestrator.events.emit import (
    AUDIENCE_REVIEWER,
    AUDIENCE_TRACE,
    EventEmitter,
    emit_stage,
    emit_text,
)
from poppy_orchestrator.hitl.pause import HitlGate
from poppy_orchestrator.receipts.emit import emit_receipt_after_approve
from poppy_orchestrator.endeavor.config import (
    ENDEAVOR_MODEL_ID,
    EndeavorConfig,
    resolve_endeavor_config,
)
from poppy_orchestrator.endeavor.summarize import (
    endeavor_stage_payload,
    summarize_claims_for_hitl,
)

# Ordered stages judges / Flower Chat can follow (F5 run-series).
FLOW_STAGES: tuple[str, ...] = (
    "kickoff",
    "claim_request.HospitalCred",
    "claim_request.PayerEnrollment",
    "claim_response.HospitalCred",
    "claim_response.PayerEnrollment",
    "claims_aggregated",
    "endeavor_assist",  # F11 optional — dry-run if no API key
    "hitl_pause",
    "claim_receipt",
    "complete",
)

_FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "providers.json"


def resolve_provider_display_name(
    provider_id: str,
    *,
    fallback: str = "Synthetic Provider P",
    fixtures_path: Optional[Path] = None,
) -> str:
    """Look up display_name from synthetic fixtures (no live directory)."""
    path = fixtures_path or _FIXTURES
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        for row in data.get("providers", []):
            if row.get("provider_id") == provider_id:
                return str(row.get("display_name") or fallback)
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return fallback


@dataclass
class OrchestratorConfig:
    """Kickoff knobs: credential provider P for network X (synthetic)."""

    provider_id: str = "SYNTH-NPI-1999999999"
    network_id: str = "SYNTH-NETWORK-X"
    display_name: str = ""
    run_id: Optional[str] = None
    model_id: Optional[str] = None  # `endeavor-model-id` of this run, if set

    def model_config(self) -> Optional[EndeavorConfig]:
        """The run's own model id wins over the environment and the default.

        On SuperGrid the Orchestrator's environment is not ours to set, so the
        run config is the only place the model can be chosen.
        """
        if not self.model_id:
            return None
        return resolve_endeavor_config({**os.environ, ENDEAVOR_MODEL_ID: self.model_id})

    def resolved_display_name(self) -> str:
        if self.display_name.strip():
            return self.display_name
        return resolve_provider_display_name(self.provider_id)


@dataclass
class FlowResult:
    run_id: str
    bundle: ClaimBundle
    hitl: Optional[HitlDecision]
    receipt: Optional[ClaimReceipt]
    outcome: CredentialingOutcome

    def to_summary(self) -> dict[str, Any]:
        """CLI / script JSON summary for F5 / F9 dry-run."""
        return {
            "run_id": self.run_id,
            "outcome": self.outcome.value,
            "provider_id": self.bundle.provider.provider_id,
            "network_id": self.bundle.provider.network_id,
            "display_name": self.bundle.provider.display_name,
            "missing_nodes": self.bundle.missing_nodes(),
            "claims": [c.to_dict() for c in self.bundle.all_claims()],
            "hitl": self.hitl.to_dict() if self.hitl else None,
            "receipt": self.receipt.to_dict() if self.receipt else None,
            "hitl_pause_reached": self.hitl is not None,
            "stages": list(FLOW_STAGES),
            "synthetic": True,
            "endeavor_optional": True,
        }


def run_credentialing_flow(
    *,
    hospital: SuperNodeClaimClient,
    payer: SuperNodeClaimClient,
    hitl_gate: HitlGate,
    emitter: EventEmitter,
    config: OrchestratorConfig,
    collect_claims: Optional[
        Callable[[dict[str, ClaimRequest]], dict[str, ClaimResponse]]
    ] = None,
) -> FlowResult:
    """F5 path: kickoff → both SuperNode claims → HITL → receipt."""
    run_id = config.run_id or f"run-{uuid.uuid4().hex[:12]}"
    provider = ProviderRef(
        provider_id=config.provider_id,
        network_id=config.network_id,
        display_name=config.resolved_display_name(),
    )

    emit_stage(
        emitter,
        "kickoff",
        {
            "provider": provider.to_dict(),
            "intent": "credential_provider_for_network",
            "nodes": ["HospitalCred", "PayerEnrollment"],
            "synthetic": True,
        },
    )
    emit_text(
        emitter,
        f"PrivCred PoppyOrchestrator kickoff: credential {provider.display_name} "
        f"({provider.provider_id}) for network {provider.network_id} "
        "[synthetic fixtures only — no live CAQH/NPDB].",
        audience=AUDIENCE_TRACE,
    )

    # --- HospitalCred ---
    hosp_req = ClaimRequest(
        request_id=new_request_id("hosp"),
        provider=provider,
        claim_types=tuple(sorted(HOSPITAL_CRED_CLAIMS)),
        source_node="HospitalCred",
    )
    emit_stage(emitter, "claim_request.HospitalCred", hosp_req.to_dict())
    pay_req = ClaimRequest(
        request_id=new_request_id("pay"),
        provider=provider,
        claim_types=tuple(sorted(PAYER_ENROLLMENT_CLAIMS)),
        source_node="PayerEnrollment",
    )
    emit_stage(emitter, "claim_request.PayerEnrollment", pay_req.to_dict())
    if collect_claims is not None:
        replies = collect_claims({"HospitalCred": hosp_req, "PayerEnrollment": pay_req})
        hosp_resp, pay_resp = replies["HospitalCred"], replies["PayerEnrollment"]
    else:
        # Local stubs need no network batching; retain the existing client contract.
        hosp_resp = hospital.request_claims(hosp_req)
        pay_resp = payer.request_claims(pay_req)
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
        conflicts=_recheck_disputed_claims(
            owner=hospital,
            owner_response=hosp_resp,
            other_response=pay_resp,
            provider=provider,
            emitter=emitter,
        ),
    )
    emit_stage(emitter, "claims_aggregated", bundle.to_dict())

    # --- F11 Endeavor assist on Orchestrator (optional; dry-run without key) ---
    endeavor = summarize_claims_for_hitl(bundle, config=config.model_config())
    emit_stage(emitter, "endeavor_assist", endeavor_stage_payload(endeavor))
    mode_tag = "LIVE" if endeavor.live_call else "DRY-RUN (endeavor_optional)"
    emit_text(
        emitter,
        f"Endeavor assist [{mode_tag}] on PoppyOrchestrator: {endeavor.text[:280]}",
        # A stand-in text is not a model's brief: keep it out of the review.
        audience=AUDIENCE_REVIEWER if endeavor.live_call else AUDIENCE_TRACE,
    )

    # --- HITL (mandatory — never silent skip) ---
    emit_stage(
        emitter,
        "hitl_pause",
        {
            "provider_id": provider.provider_id,
            "claim_count": len(bundle.all_claims()),
            "missing_nodes": bundle.missing_nodes(),
        },
    )
    hitl = hitl_gate.wait_for_decision(bundle, emitter)
    return finalize_credentialing_flow(bundle=bundle, hitl=hitl, emitter=emitter)


def finalize_credentialing_flow(
    *, bundle: ClaimBundle, hitl: HitlDecision, emitter: EventEmitter
) -> FlowResult:
    """Complete the exact reviewed bundle, including a resumed Flower Chat run."""
    run_id = bundle.run_id
    outcome = _map_outcome(hitl, bundle)

    # F8: auditable receipt ONLY after HITL Approve (escalate/reject → None)
    receipt = emit_receipt_after_approve(
        run_id=run_id,
        bundle=bundle,
        hitl=hitl,
        outcome=outcome,
        emitter=emitter,
        run_series=FLOW_STAGES,
    )

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


def _recheck_disputed_claims(
    *,
    owner: SuperNodeClaimClient,
    owner_response: ClaimResponse,
    other_response: ClaimResponse,
    provider: ProviderRef,
    emitter: EventEmitter,
) -> tuple[ClaimConflict, ...]:
    """Second round: re-ask the owner once per claim the other node disputes."""
    if not (owner_response.ok and other_response.ok):
        return ()
    conflicts: list[ClaimConflict] = []
    for dispute in other_response.disputes:
        first = owner_response.get(dispute.claim_type)
        if first is None or first.value == dispute.observed:
            continue
        node = owner_response.source_node
        emit_stage(
            emitter,
            "conflict_detected",
            {"owner": node, "asserted": first.value, "dispute": dispute.to_dict()},
        )
        emit_text(
            emitter,
            f"Sources disagree on {dispute.claim_type}: {node} says {first.value!r}, "
            f"{dispute.raised_by} sees {dispute.observed!r} "
            f"({dispute.period or 'no period given'}). Asking {node} to look again.",
        )
        request = ClaimRequest(
            request_id=new_request_id("recheck"),
            provider=provider,
            claim_types=(dispute.claim_type,),
            source_node=node,
            recheck=dispute,
        )
        emit_stage(emitter, f"claim_recheck_request.{node}", request.to_dict())
        response = owner.request_claims(request)
        emit_stage(emitter, f"claim_recheck_response.{node}", response.to_dict())
        errors = validate_claim_response(
            response, request.claim_types, allowed_for_node=HOSPITAL_CRED_CLAIMS
        )
        conflict = ClaimConflict(
            claim_type=dispute.claim_type,
            owner=node,
            asserted=first.value,
            dispute=dispute,
            follow_up=None if errors else response.get(dispute.claim_type),
        )
        emit_text(
            emitter,
            f"{node} looked again at {dispute.claim_type}: {conflict.status}.",
        )
        conflicts.append(conflict)
    return tuple(conflicts)


def _map_outcome(hitl: HitlDecision, bundle: ClaimBundle) -> CredentialingOutcome:
    if hitl.action == HitlAction.REJECT:
        return CredentialingOutcome.REJECTED
    if hitl.action == HitlAction.ESCALATE:
        return CredentialingOutcome.ESCALATED
    # Approve path: still fail closed if a node was missing
    if bundle.missing_nodes():
        return CredentialingOutcome.FAILED
    # ... or while two sources still disagree
    if bundle.unresolved_conflicts():
        return CredentialingOutcome.FAILED
    return CredentialingOutcome.CREDENTIALED
