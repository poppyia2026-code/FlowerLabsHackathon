"""Orchestrator-role Endeavor assist: synthesize claim bundle for HITL (F11).

Synthetic fixtures only. Used on PoppyOrchestrator (≥1 role) before HITL pause.
"""

from __future__ import annotations

from typing import Any, Optional

from poppy_orchestrator.contracts.claims import ClaimBundle, ClaimResponse
from poppy_orchestrator.endeavor.client import EndeavorClient, EndeavorResult
from poppy_orchestrator.endeavor.config import EndeavorConfig, resolve_endeavor_config

INSTRUCTIONS = (
    "You are PoppyOrchestrator on Flower SuperGrid. Summarize synthetic "
    "verification claims for a human HITL reviewer. Never invent live CAQH/NPDB "
    "data. Never claim HIPAA certification or HITRUST. Be concise (≤80 words)."
)


def _claims_lines(resp: Optional[ClaimResponse]) -> list[str]:
    if resp is None:
        return ["  (node missing)"]
    if not resp.ok:
        return [f"  (node error: {resp.error})"]
    lines: list[str] = []
    for claim in resp.claims:
        lines.append(
            f"  - [{resp.source_node}] {claim.claim_type}={claim.value!r} "
            f"conf={claim.confidence} evidence={claim.evidence_ref}"
        )
    return lines or ["  (no claims)"]


def build_claim_summary_prompt(bundle: ClaimBundle) -> str:
    """Build a synthetic-only prompt from aggregated claims."""
    lines = [
        f"Provider: {bundle.provider.display_name} ({bundle.provider.provider_id})",
        f"Network: {bundle.provider.network_id}",
        f"Run: {bundle.run_id}",
        f"Missing nodes: {bundle.missing_nodes() or 'none'}",
        "HospitalCred claims (synthetic fixtures):",
        *_claims_lines(bundle.hospital),
        "PayerEnrollment claims (synthetic fixtures):",
        *_claims_lines(bundle.payer),
        "Task: 2–3 sentence HITL brief — what looks ready to Approve vs Escalate.",
    ]
    return "\n".join(lines)


def summarize_claims_for_hitl(
    bundle: ClaimBundle,
    *,
    client: Optional[EndeavorClient] = None,
    config: Optional[EndeavorConfig] = None,
) -> EndeavorResult:
    """Invoke Endeavor (or dry-run stub) on the Orchestrator role."""
    cfg = config or resolve_endeavor_config()
    cli = client or EndeavorClient(cfg)
    prompt = build_claim_summary_prompt(bundle)
    result = cli.complete(prompt=prompt, instructions=INSTRUCTIONS)
    result.meta = {
        **result.meta,
        "endeavor_optional": True,
        "role": cfg.role,
        "claim_count": len(bundle.all_claims()),
        "provider_id": bundle.provider.provider_id,
        "synthetic": True,
    }
    return result


def endeavor_stage_payload(result: EndeavorResult) -> dict[str, Any]:
    """Payload for privcred.stage endeavor_assist (judge-visible honesty)."""
    return {
        "endeavor": result.to_dict(),
        "endeavor_optional": True,
        "spoken_demo_beat": "3:00–3:40 — Orchestrator reasoning is on Endeavor (if live)",
    }
