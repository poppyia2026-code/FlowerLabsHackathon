"""Local FakeAgentGrid — mirrors Flower RuntimeAgentGrid tool surface.

Used for dry-run / unit tests when SuperGrid is unavailable.
Tool names match flwr.supercore.task_process.agent.grid:
  get_nodes · push_messages · pull_messages · push_reply_message
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


@dataclass(frozen=True)
class FakeGridNode:
    node_id: str
    name: str
    location: Optional[str] = None


def _default_nodes() -> list[FakeGridNode]:
    return [
        FakeGridNode("1001", ROLE_HOSPITAL_CRED, "synth://hospital-cred"),
        FakeGridNode("1002", ROLE_PAYER_ENROLLMENT, "synth://payer-enrollment"),
    ]


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
                # Synthesize role reply immediately (judge-visible handoff).
                node = next((n for n in self.nodes if n.node_id == dst), None)
                role = node.name if node else f"node-{dst}"
                reply_id = f"msg-{uuid.uuid4().hex[:12]}"
                self._pending[mid]["synthetic_reply"] = {
                    "message_id": reply_id,
                    "reply_to_message_id": mid,
                    "src_node_id": dst,
                    "payload": (
                        f"[{role}] ACK synthetic claim handoff — "
                        f"payload_len={len(payload)} (fixtures only, no PHI)."
                    ),
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
        mid = f"msg-{uuid.uuid4().hex[:12]}"
        return {"message_id": mid, "error": None}
