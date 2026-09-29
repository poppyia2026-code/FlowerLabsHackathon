"""Real Grid claim collection and a human review across Flower Chat turns.

No local fixture fallback and no automatic approval are available on this path.
The same FAB runs at the coordinator and at each locally configured SuperNode.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

from poppy_orchestrator.clients.grid_clients import GridHospitalCredClient, GridPayerEnrollmentClient
from poppy_orchestrator.contracts.claims import (
    ClaimBundle, HitlAction, HitlDecision, ProviderRef, claim_response_from_dict,
)
from poppy_orchestrator.events.emit import flower_emitter_from_session
from poppy_orchestrator.hitl.pause import HitlGate, _emit_hitl_request
from poppy_orchestrator.orchestration.flow import (
    OrchestratorConfig, finalize_credentialing_flow, run_credentialing_flow,
)
from poppy_orchestrator.supernodes.runtime import serve_runtime_instruction

STATE_KEY = "poppy-review"


class ReviewRequired(Exception):
    def __init__(self, bundle: ClaimBundle) -> None:
        super().__init__("Human review required")
        self.bundle = bundle


class FlowerChatReviewGate(HitlGate):
    def wait_for_decision(self, bundle, emitter, *, timeout_s=None):
        _emit_hitl_request(emitter, bundle)
        raise ReviewRequired(bundle)


def _save(context: Any, record: dict[str, Any]) -> None:
    from flwr.app import ConfigRecord

    context.state[STATE_KEY] = ConfigRecord({"json": json.dumps(record)})


def _load(context: Any) -> dict[str, Any]:
    record = context.state.get(STATE_KEY)
    return json.loads(record["json"]) if record else {}


def _reply(agent: Any, text: str) -> None:
    agent.events.emit({"type": "response.output_text.delta", "delta": text})
    agent.events.emit({"type": "response.completed"})


def _bundle_from_dict(data: dict[str, Any]) -> ClaimBundle:
    return ClaimBundle(
        run_id=data["run_id"],
        provider=ProviderRef(**data["provider"]),
        hospital=claim_response_from_dict(data["hospital"]) if data.get("hospital") else None,
        payer=claim_response_from_dict(data["payer"]) if data.get("payer") else None,
        collected_at=data["collected_at"],
    )


def _review_text(bundle: ClaimBundle) -> str:
    rows = [f"**Synthetic review {bundle.run_id}**", f"Provider: {bundle.provider.provider_id}",
            f"Network: {bundle.provider.network_id}", "", "Verified claims:"]
    for response in (bundle.hospital, bundle.payer):
        if response is not None:
            if not response.ok:
                rows.append(f"- {response.source_node}: unavailable — {response.error}")
            else:
                rows.extend(f"- {response.source_node}: {c.claim_type} = {c.value}"
                            for c in response.claims)
    rows.extend(["", "No receipt has been issued. Review the evidence, then send one command:",
                 f"`/approve {bundle.run_id}`", f"`/escalate {bundle.run_id} reason`",
                 f"`/reject {bundle.run_id} reason`"])
    return "\n".join(rows)


def run_live_agent(agent: Any, context: Any) -> None:
    grid = getattr(agent, "grid", None)
    if grid is None:
        raise RuntimeError("Flower Grid is required; use the explicit dry-run scripts offline")
    tool_names = {tool.get("name") for tool in grid.tools()}
    if "push_reply_message" in tool_names and "get_nodes" not in tool_names:
        serve_runtime_instruction(agent, context)
        return
    if not {"get_nodes", "push_messages", "pull_messages"} <= tool_names:
        raise RuntimeError("The coordinator needs Flower Grid messaging tools")

    config = context.run_config
    if str(config.get("hitl-auto-approve-dry-run", "false")).lower() in {"true", "1", "yes"}:
        raise ValueError("Automatic approval is disabled for Flower runs; use dry-run scripts")
    prompt = agent.prompt.strip()
    pending = _load(context)
    command = re.fullmatch(r"/(approve|escalate|reject)\s+(\S+)(?:\s+(.+))?", prompt, re.S)
    if command:
        action, review_id, reason = command.groups()
        if pending.get("status") != "pending" or pending.get("bundle", {}).get("run_id") != review_id:
            _reply(agent, "No pending review matches that ID. No decision was applied.")
            return
        bundle = _bundle_from_dict(pending["bundle"])
        if time.time() - bundle.collected_at > float(config.get("review-max-age-seconds", 600)):
            _save(context, {"status": "expired", "review_id": review_id})
            _reply(agent, "This review expired. Start a new verification to collect fresh claims.")
            return
        hitl = HitlDecision(action=HitlAction(action), actor="flower-chat-reviewer", reason=reason or "")
        result = finalize_credentialing_flow(
            bundle=bundle, hitl=hitl, emitter=flower_emitter_from_session(agent),
        )
        _save(context, {"status": "completed", "result": result.to_summary()})
        _reply(agent, f"Synthetic review outcome: **{result.outcome.value}**\n\n"
               + (f"Receipt: `{result.receipt.receipt_id}`" if result.receipt else "No receipt issued."))
        return
    if prompt.startswith(("/approve", "/escalate", "/reject")):
        _reply(agent, "Include the review ID in the decision command. No decision was applied.")
        return
    if pending.get("status") == "pending":
        _reply(agent, _review_text(_bundle_from_dict(pending["bundle"])))
        return

    provider_ids = re.findall(r"SYNTH-NPI-\d+", prompt)
    networks = re.findall(r"SYNTH-NETWORK-[A-Za-z0-9-]+", prompt)
    provider_id = provider_ids[0] if provider_ids else str(config.get("provider-id", "SYNTH-NPI-1999999999"))
    network_id = networks[0] if networks else str(config.get("network-id", "SYNTH-NETWORK-X"))
    timeout = float(config.get("grid-pull-timeout", 30))
    try:
        run_credentialing_flow(
            hospital=GridHospitalCredClient(grid, pull_timeout=timeout),
            payer=GridPayerEnrollmentClient(grid, pull_timeout=timeout),
            hitl_gate=FlowerChatReviewGate(),
            emitter=flower_emitter_from_session(agent),
            config=OrchestratorConfig(provider_id=provider_id, network_id=network_id,
                                      display_name="Synthetic provider",
                                      run_id=f"run-{context.run_id}"),
        )
    except ReviewRequired as review:
        _save(context, {"status": "pending", "bundle": review.bundle.to_dict()})
        _reply(agent, _review_text(review.bundle))
