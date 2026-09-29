"""SuperNode side of the AgentApp: answer one Orchestrator claim request.

Flower loads the single ``agentapp`` component of the FAB on the SuperLink
and on every SuperNode, so the same ``main`` has to work out where it is
running. The runtime gives each side a different Grid tool set: the SuperLink
gets ``get_nodes`` / ``push_messages`` / ``pull_messages``, a SuperNode gets
only ``push_reply_message``.

On a SuperNode the instruction arrives as ``agent.prompt``, a JSON string
``{"message_id", "src_node_id", "payload"}`` whose ``payload`` is the
Orchestrator's claim request. The role to play is the request's ``to`` field.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from poppy_orchestrator.grid.roles import PRIVCRED_GRID_ROLES
from poppy_orchestrator.supernodes.claim_service import handle_inbound_message

REPLY_TOOL = "push_reply_message"
SUPERLINK_ONLY_TOOL = "get_nodes"


def is_supernode_session(agent: Any) -> bool:
    """True when the runtime exposed the SuperNode Grid tool set."""
    grid = getattr(agent, "grid", None)
    if grid is None or not hasattr(grid, "tools"):
        return False
    names = {tool.get("name") for tool in grid.tools()}
    return REPLY_TOOL in names and SUPERLINK_ONLY_TOOL not in names


def parse_instruction(prompt: str) -> dict[str, Any]:
    """Return the Orchestrator request carried by a Grid instruction prompt."""
    try:
        envelope = json.loads(prompt)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError(f"instruction is not JSON: {exc}") from exc
    if not isinstance(envelope, dict):
        raise ValueError("instruction is not a JSON object")
    payload = envelope.get("payload", envelope)
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError(f"instruction payload is not JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("instruction payload is not a JSON object")
    return payload


def build_reply(prompt: str) -> tuple[str, str]:
    """Return ``(role, reply_json)`` for one inbound instruction."""
    try:
        request = parse_instruction(prompt)
    except ValueError as exc:
        return "unknown", _error_reply("unknown", str(exc))
    role = str(request.get("to") or "")
    if role not in PRIVCRED_GRID_ROLES:
        return role or "unknown", _error_reply(
            role or "unknown",
            f"unknown role {role!r}; expected one of {list(PRIVCRED_GRID_ROLES)}",
        )
    return role, handle_inbound_message(role, request)


def _error_reply(role: str, reason: str) -> str:
    return json.dumps(
        {"ok": False, "error": reason, "source_node": role, "synthetic": True},
        separators=(",", ":"),
    )


def run_supernode_role(agent: Any, context: Any) -> str:
    """Answer the Orchestrator request and return the role that was played."""
    role, reply = build_reply(getattr(agent, "prompt", "") or "")
    result = agent.grid.call(
        {
            "type": "function_call",
            "name": REPLY_TOOL,
            "call_id": f"privcred-reply-{uuid.uuid4().hex[:8]}",
            "arguments": {"payload": reply},
        }
    )
    raw = result.get("output", "{}")
    output = json.loads(raw) if isinstance(raw, str) else raw
    if output.get("error") or not output.get("message_id"):
        raise RuntimeError(
            f"{role} could not reply to the Orchestrator: "
            f"{output.get('error') or 'reply was not accepted'}"
        )

    state = getattr(context, "state", None)
    if state is not None and hasattr(state, "__setitem__"):
        try:
            state["privcred_role"] = role
            state["privcred_synthetic"] = True
        except Exception:
            pass
    return role
