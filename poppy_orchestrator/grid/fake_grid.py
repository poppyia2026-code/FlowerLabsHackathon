"""Local FakeAgentGrid — mirrors Flower RuntimeAgentGrid tool surface.

Used for dry-run / unit tests when SuperGrid is unavailable.
Tool names match flwr AgentGrid:
  get_nodes · push_messages · pull_messages · push_reply_message

Auto-replies return synthetic claim JSON via stub clients / fixtures
(F5/F6 contract) — never live CAQH/NPDB/PHI.
"""

from __future__ import annotations

import json
import random
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from poppy_orchestrator.grid.roles import (
    ROLE_HOSPITAL_CRED,
    ROLE_PAYER_ENROLLMENT,
)

# Stable fake uint64 decimal strings (judge-visible node ids).
HOSPITAL_CRED_NODE_ID = "9000000000000001001"
PAYER_ENROLLMENT_NODE_ID = "9000000000000001002"


@dataclass(frozen=True)
class FakeGridNode:
    node_id: str
    name: str
    location: Optional[str] = None


def _default_nodes() -> list[FakeGridNode]:
    return [
        FakeGridNode(
            HOSPITAL_CRED_NODE_ID, ROLE_HOSPITAL_CRED, "synth://hospital-cred"
        ),
        FakeGridNode(
            PAYER_ENROLLMENT_NODE_ID,
            ROLE_PAYER_ENROLLMENT,
            "synth://payer-enrollment",
        ),
    ]


def _synthetic_claim_reply(role: str, inbound_payload: str) -> str:
    """Build synthetic ClaimResponse JSON via F2/F3 SuperNode claim service."""
    # Imported here: claim_service -> clients -> grid -> this module is a cycle.
    from poppy_orchestrator.supernodes.claim_service import handle_inbound_message

    return handle_inbound_message(role, inbound_payload)


@dataclass
class FakeAgentGrid:
    """In-process AgentGrid stand-in with synthetic HospitalCred + PayerEnrollment."""

    nodes: list[FakeGridNode] = field(default_factory=_default_nodes)
    events: list[dict[str, Any]] = field(default_factory=list)
    _pending: dict[str, dict[str, Any]] = field(default_factory=dict)
    _auto_reply: bool = True

    def tools(self) -> list[dict[str, Any]]:
        return [
            {"name": "get_nodes", "type": "function"},
            {"name": "push_messages", "type": "function"},
            {"name": "pull_messages", "type": "function"},
            {"name": "push_reply_message", "type": "function"},
        ]

    def call(self, tool_call: dict[str, Any]) -> dict[str, Any]:
        name = tool_call["name"]
        call_id = tool_call.get("call_id") or f"call-{uuid.uuid4().hex[:8]}"
        arguments = tool_call.get("arguments", {})
        if isinstance(arguments, str):
            arguments = json.loads(arguments)

        self.events.append(
            {
                "type": "function_call",
                "call_id": call_id,
                "name": name,
                "arguments": json.dumps(arguments, separators=(",", ":")),
            }
        )
        handler = getattr(self, f"_{name}")
        output = handler(**arguments)
        output_item = {
            "type": "function_call_output",
            "call_id": call_id,
            "output": json.dumps(output, separators=(",", ":")),
        }
        self.events.append(output_item)
        return output_item

    def _get_nodes(self, sample_size: Optional[int] = None) -> dict[str, Any]:
        nodes = list(self.nodes)
        if sample_size is not None and sample_size < 1:
            raise ValueError("Grid sample size must be positive.")
        selected = (
            nodes
            if sample_size is None
            else random.sample(nodes, min(sample_size, len(nodes)))
        )
        return {
            "nodes": [
                {"id": n.node_id, "name": n.name, "location": n.location}
                for n in selected
            ],
            "num_available": len(nodes),
        }

    def _push_messages(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        results: list[dict[str, Any]] = []
        for item in messages:
            mid = f"msg-{uuid.uuid4().hex[:12]}"
            dst = str(item["dst_node_id"])
            payload = str(item["payload"])
            self._pending[mid] = {
                "dst_node_id": dst,
                "payload": payload,
                "reply_to_message_id": item.get("reply_to_message_id"),
            }
            if self._auto_reply:
                node = next((n for n in self.nodes if n.node_id == dst), None)
                role = node.name if node else f"node-{dst}"
                reply_id = f"msg-{uuid.uuid4().hex[:12]}"
                self._pending[mid]["synthetic_reply"] = {
                    "message_id": reply_id,
                    "reply_to_message_id": mid,
                    "src_node_id": dst,
                    "payload": _synthetic_claim_reply(role, payload),
                    "error": None,
                }
            results.append({"message_id": mid, "error": None})
        return {"results": results}

    def _pull_messages(
        self, message_ids: list[str], timeout: float = 0.0
    ) -> dict[str, Any]:
        _ = timeout
        messages: list[dict[str, Any]] = []
        pending: list[str] = []
        for mid in message_ids:
            entry = self._pending.get(mid)
            if entry and "synthetic_reply" in entry:
                messages.append(entry["synthetic_reply"])
            else:
                pending.append(mid)
        return {"messages": messages, "pending_message_ids": pending}

    def _push_reply_message(self, payload: str) -> dict[str, Any]:
        _ = payload
        mid = f"msg-{uuid.uuid4().hex[:12]}"
        return {"message_id": mid, "error": None}
