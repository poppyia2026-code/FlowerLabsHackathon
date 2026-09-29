"""F0 Grid role handoff: Orchestrator ↔ HospitalCred / PayerEnrollment.

Judge-visible path (Flower Chat / flwr log / dry-run events):
  1. agent.grid.call get_nodes(sample_size=…)  — sample SuperNodes
  2. agent.grid.call push_messages             — claim-request payloads
  3. agent.grid.call pull_messages             — synthetic / live replies

Works with RuntimeAgentGrid (SuperGrid) or FakeAgentGrid (local).
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol

from poppy_orchestrator.events.emit import EventEmitter, LocalEventBus, emit_stage, emit_text
from poppy_orchestrator.grid.roles import (
    PRIVCRED_GRID_ROLES,
    ROLE_HOSPITAL_CRED,
    ROLE_ORCHESTRATOR,
    ROLE_PAYER_ENROLLMENT,
)


def emit_grid_event(
    emitter: EventEmitter, name: str, data: dict[str, Any] | None = None
) -> None:
    """Judge-visible Grid tool event (privcred.grid.*)."""
    emitter.emit(
        {
            "event": f"privcred.grid.{name}",
            "data": {**(data or {}), "synthetic": True},
        }
    )


class GridLike(Protocol):
    def tools(self) -> list[Any]: ...

    def call(self, tool_call: dict[str, Any]) -> dict[str, Any]: ...


@dataclass
class GridHandoffResult:
    """Outcome of a synthetic Multi-role Grid tools handoff."""

    ok: bool
    roles_contacted: list[str] = field(default_factory=list)
    nodes_sampled: list[dict[str, Any]] = field(default_factory=list)
    push_results: list[dict[str, Any]] = field(default_factory=list)
    replies: list[dict[str, Any]] = field(default_factory=list)
    missing_roles: list[str] = field(default_factory=list)
    tool_events: list[dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None

    def to_summary(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "roles_contacted": self.roles_contacted,
            "nodes_sampled": self.nodes_sampled,
            "push_count": len(self.push_results),
            "reply_count": len(self.replies),
            "missing_roles": self.missing_roles,
            "error": self.error,
            "synthetic": True,
        }


def _parse_output(tool_result: dict[str, Any]) -> dict[str, Any]:
    raw = tool_result.get("output", "{}")
    if isinstance(raw, dict):
        return raw
    return json.loads(raw)


def _grid_call(
    grid: GridLike,
    name: str,
    arguments: dict[str, Any],
    *,
    tool_events: list[dict[str, Any]],
) -> dict[str, Any]:
    call_id = f"privcred-{name}-{uuid.uuid4().hex[:8]}"
    tool_call = {
        "type": "function_call",
        "name": name,
        "call_id": call_id,
        "arguments": arguments,
    }
    result = grid.call(tool_call)
    tool_events.append({"name": name, "call_id": call_id, "result": result})
    return _parse_output(result)


def _match_role(node: dict[str, Any], role: str) -> bool:
    name = (node.get("name") or "").strip()
    return name.lower() == role.lower() or role.lower() in name.lower()


def run_grid_role_handoff(
    grid: GridLike,
    *,
    provider_id: str = "SYNTH-NPI-1999999999",
    network_id: str = "SYNTH-NETWORK-X",
    roles: tuple[str, ...] = PRIVCRED_GRID_ROLES,
    sample_size: Optional[int] = None,
    pull_timeout: float = 0.0,
    emitter: Optional[EventEmitter] = None,
) -> GridHandoffResult:
    """Sample Grid nodes and message ≥2 PrivCred roles via agent.grid tools.

    Synthetic payloads only — no live CAQH/NPDB/PHI.
    """
    bus: EventEmitter = emitter or LocalEventBus()
    tool_events: list[dict[str, Any]] = []

    emit_stage(
        bus,
        "grid.handoff.start",
        {
            "orchestrator": ROLE_ORCHESTRATOR,
            "target_roles": list(roles),
            "provider_id": provider_id,
            "network_id": network_id,
            "synthetic": True,
        },
    )
    emit_text(
        bus,
        (
            f"{ROLE_ORCHESTRATOR} Grid tools handoff: sample SuperNodes then "
            f"message {', '.join(roles)} for provider {provider_id} / "
            f"network {network_id} [synthetic]."
        ),
    )

    try:
        nodes_out = _grid_call(
            grid,
            "get_nodes",
            {"sample_size": sample_size},
            tool_events=tool_events,
        )
    except Exception as exc:  # pragma: no cover - defensive
        err = f"get_nodes failed: {exc}"
        emit_stage(bus, "grid.handoff.error", {"error": err})
        return GridHandoffResult(ok=False, error=err, tool_events=tool_events)

    sampled = list(nodes_out.get("nodes") or [])
    emit_stage(
        bus,
        "grid.get_nodes",
        {
            "num_available": nodes_out.get("num_available"),
            "sampled": sampled,
            "tool": "get_nodes",
        },
    )
    emit_grid_event(
        bus,
        "get_nodes",
        {
            "num_available": nodes_out.get("num_available"),
            "sampled": sampled,
            "tool": "get_nodes",
        },
    )

    role_to_node: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    for role in roles:
        match = next((n for n in sampled if _match_role(n, role)), None)
        if match is None:
            # Fallback: search is only within sample; mark missing.
            missing.append(role)
        else:
            role_to_node[role] = match

    if missing:
        # Retry get_nodes with full set (sample_size=null) once if sample missed roles.
        if sample_size is not None:
            full = _grid_call(
                grid,
                "get_nodes",
                {"sample_size": None},
                tool_events=tool_events,
            )
            sampled = list(full.get("nodes") or [])
            role_to_node = {}
            missing = []
            for role in roles:
                match = next((n for n in sampled if _match_role(n, role)), None)
                if match is None:
                    missing.append(role)
                else:
                    role_to_node[role] = match

    if len(role_to_node) < 2:
        err = (
            f"Need ≥2 Grid roles for F0; found {list(role_to_node)} "
            f"missing={missing}"
        )
        emit_stage(bus, "grid.handoff.error", {"error": err, "missing": missing})
        return GridHandoffResult(
            ok=False,
            roles_contacted=list(role_to_node),
            nodes_sampled=sampled,
            missing_roles=missing,
            tool_events=tool_events,
            error=err,
        )

    messages: list[dict[str, Any]] = []
    for role, node in role_to_node.items():
        payload = json.dumps(
            {
                "from": ROLE_ORCHESTRATOR,
                "to": role,
                "intent": "request_verification_claims",
                "provider_id": provider_id,
                "network_id": network_id,
                "synthetic": True,
                "note": "fixtures only — no live PHI / CAQH / NPDB",
            },
            separators=(",", ":"),
        )
        messages.append(
            {
                "dst_node_id": str(node["id"]),
                "payload": payload,
                "reply_to_message_id": None,
            }
        )

    push_out = _grid_call(
        grid,
        "push_messages",
        {"messages": messages},
        tool_events=tool_events,
    )
    push_results = list(push_out.get("results") or [])
    emit_stage(
        bus,
        "grid.push_messages",
        {
            "roles": list(role_to_node),
            "results": push_results,
            "tool": "push_messages",
        },
    )
    emit_grid_event(
        bus,
        "push",
        {
            "roles": list(role_to_node),
            "results": push_results,
            "tool": "push_messages",
        },
    )

    message_ids = [
        r["message_id"] for r in push_results if r.get("message_id")
    ]
    replies: list[dict[str, Any]] = []
    if message_ids:
        pull_out = _grid_call(
            grid,
            "pull_messages",
            {"message_ids": message_ids, "timeout": pull_timeout},
            tool_events=tool_events,
        )
        replies = list(pull_out.get("messages") or [])
        emit_stage(
            bus,
            "grid.pull_messages",
            {
                "replies": replies,
                "pending": pull_out.get("pending_message_ids"),
                "tool": "pull_messages",
            },
        )
        emit_grid_event(
            bus,
            "pull",
            {
                "replies": replies,
                "pending": pull_out.get("pending_message_ids"),
                "tool": "pull_messages",
            },
        )

    ok = len(replies) >= 2 and not missing
    emit_stage(
        bus,
        "grid.handoff.complete",
        {
            "ok": ok,
            "roles_contacted": list(role_to_node),
            "reply_count": len(replies),
            "missing_roles": missing,
        },
    )
    emit_grid_event(
        bus,
        "handoff",
        {
            "ok": ok,
            "roles_contacted": list(role_to_node),
            "reply_count": len(replies),
            "missing_roles": missing,
        },
    )
    emit_text(
        bus,
        (
            f"Grid handoff complete: contacted {list(role_to_node.keys())}, "
            f"replies={len(replies)}, ok={ok} [synthetic AgentApp Grid tools]."
        ),
    )

    return GridHandoffResult(
        ok=ok,
        roles_contacted=list(role_to_node.keys()),
        nodes_sampled=sampled,
        push_results=push_results,
        replies=replies,
        missing_roles=missing,
        tool_events=tool_events,
        error=None if ok else "incomplete Grid replies or missing roles",
    )


# Re-export role names for callers that import from handoff.
__all__ = [
    "GridHandoffResult",
    "GridLike",
    "ROLE_HOSPITAL_CRED",
    "ROLE_ORCHESTRATOR",
    "ROLE_PAYER_ENROLLMENT",
    "run_grid_role_handoff",
]
