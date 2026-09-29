"""Coordinator and SuperNodes running the same ``main`` in one round trip.

``test_live_runtime.py`` checks each side on its own. Here a coordinator push
actually runs ``main`` on the receiving node, so the request the coordinator
builds is the one the node has to accept, and the reply the node builds is
the one the coordinator has to accept.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional
from unittest.mock import patch

import pytest

from poppy_orchestrator.agent_app import main
from poppy_orchestrator.live_runtime import STATE_KEY

pytest.importorskip("flwr.app")

ROOT = Path(__file__).resolve().parents[1]
ROLES = ("HospitalCred", "PayerEnrollment")
COORDINATOR_TOOLS = {"get_nodes", "push_messages", "pull_messages"}
NODE_TOOLS = {"push_reply_message"}
COORDINATOR_NODE_ID = "1"


class StrictEvents:
    """Rejects what ``RuntimeAgentEvents.emit`` rejects."""

    def __init__(self) -> None:
        self.items: list[dict[str, Any]] = []

    def emit(self, event: dict[str, Any]) -> None:
        if not isinstance(event.get("type"), str) or not event["type"]:
            raise ValueError("Run event requires a non-empty string 'type' field.")
        self.items.append(event)


class ToolGrid:
    names: set[str] = set()

    def tools(self) -> list[dict[str, Any]]:
        return [{"type": "function", "name": name} for name in sorted(self.names)]

    def call(self, tool_call: dict[str, Any]) -> dict[str, Any]:
        name = tool_call["name"]
        if name not in self.names:
            raise ValueError(f"Unsupported Grid tool '{name}'.")
        output = getattr(self, f"_{name}")(**tool_call["arguments"])
        return {"type": "function_call_output", "output": json.dumps(output)}


class Federation:
    def __init__(self, offline: tuple[str, ...] = ()) -> None:
        self.nodes = [
            {"id": str(11 + index), "name": role, "location": None}
            for index, role in enumerate(ROLES)
        ]
        self.offline = offline
        self.replies: dict[str, dict[str, Any]] = {}
        self.files_read: dict[str, str] = {}
        self._count = 0

    def next_id(self) -> str:
        self._count += 1
        return f"msg-{self._count}"

    def deliver(self, node: dict[str, Any], message_id: str, payload: str) -> None:
        role = node["name"]
        if role in self.offline:
            return
        data = ROOT / "fixtures" / "supernodes" / role / "providers.json"
        self.files_read[role] = str(data)
        agent = SimpleNamespace(
            prompt=json.dumps(
                {
                    "message_id": message_id,
                    "src_node_id": COORDINATOR_NODE_ID,
                    "payload": payload,
                }
            ),
            grid=NodeGrid(self, node["id"], message_id),
            events=StrictEvents(),
        )
        context = SimpleNamespace(
            node_config={"poppy-role": role, "poppy-data": str(data)},
            state={},
            run_config={},
        )
        main(agent, context)


class CoordinatorGrid(ToolGrid):
    names = COORDINATOR_TOOLS

    def __init__(self, federation: Federation) -> None:
        self.federation = federation
        self.pushes = 0

    def _get_nodes(self, sample_size: Optional[int]) -> dict[str, Any]:
        nodes = self.federation.nodes
        return {"nodes": nodes, "num_available": len(nodes)}

    def _push_messages(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        results = []
        for message in messages:
            self.pushes += 1
            node = next(
                n for n in self.federation.nodes if n["id"] == message["dst_node_id"]
            )
            message_id = self.federation.next_id()
            self.federation.deliver(node, message_id, message["payload"])
            results.append({"message_id": message_id, "error": None})
        return {"results": results}

    def _pull_messages(self, message_ids: list[str], timeout: float) -> dict[str, Any]:
        replies = self.federation.replies
        return {
            "messages": [replies[m] for m in message_ids if m in replies],
            "pending_message_ids": [m for m in message_ids if m not in replies],
        }


class NodeGrid(ToolGrid):
    names = NODE_TOOLS

    def __init__(self, federation: Federation, node_id: str, message_id: str) -> None:
        self.federation = federation
        self.node_id = node_id
        self.message_id: Optional[str] = message_id

    def _push_reply_message(self, payload: str) -> dict[str, Any]:
        if self.message_id is None:
            return {"message_id": None, "error": "No instruction message to reply to."}
        reply_id = self.federation.next_id()
        self.federation.replies[self.message_id] = {
            "message_id": reply_id,
            "reply_to_message_id": self.message_id,
            "src_node_id": self.node_id,
            "payload": payload,
            "error": None,
        }
        self.message_id = None
        return {"message_id": reply_id, "error": None}


class Chat:
    """One Flower Chat conversation: state survives between turns."""

    def __init__(self, federation: Federation) -> None:
        from flwr.app import Context, RecordDict

        self.grid = CoordinatorGrid(federation)
        self.context = Context(
            run_id=100,
            node_id=1,
            node_config={},
            state=RecordDict(),
            run_config={"grid-pull-timeout": 1},
        )
        self.events = StrictEvents()

    def send(self, prompt: str) -> None:
        agent = SimpleNamespace(grid=self.grid, events=self.events, prompt=prompt)
        with patch.dict(os.environ, {"ENDEAVOR_ENABLED": "0"}):
            main(agent, self.context)
        self.context.run_id += 1

    def record(self) -> dict[str, Any]:
        return json.loads(self.context.state[STATE_KEY]["json"])

    def text(self) -> str:
        return "".join(
            e["delta"]
            for e in self.events.items
            if e["type"] == "response.output_text.delta"
        )


def test_doubles_match_flwr_tool_names() -> None:
    grid = pytest.importorskip("flwr.supercore.task_process.agent.grid")
    assert grid._GRID_TOOL_NAMES == COORDINATOR_TOOLS
    assert grid._SUPERNODE_GRID_TOOL_NAMES == NODE_TOOLS


def test_review_waits_for_a_person_then_approval_issues_the_receipt() -> None:
    federation = Federation()
    chat = Chat(federation)

    chat.send("Verify SYNTH-NPI-1999999999 for SYNTH-NETWORK-X")

    assert chat.record()["status"] == "pending"
    assert "/approve run-100" in chat.text()
    assert set(federation.replies) and len(federation.replies) == 2
    pushes_before_decision = chat.grid.pushes

    chat.send("/approve run-100")

    result = chat.record()["result"]
    assert result["outcome"] == "credentialed"
    assert result["receipt"]
    assert chat.grid.pushes == pushes_before_decision
    assert chat.events.items[-1]["type"] == "response.completed"


def test_claims_in_the_review_are_the_ones_the_nodes_sent() -> None:
    federation = Federation()
    chat = Chat(federation)

    chat.send("Verify SYNTH-NPI-1999999999 for SYNTH-NETWORK-X")

    sent = {
        (body["source_node"], claim["claim_type"], claim["value"])
        for body in (json.loads(r["payload"]) for r in federation.replies.values())
        for claim in body["claims"]
    }
    bundle = chat.record()["bundle"]
    reviewed = {
        (side["source_node"], claim["claim_type"], claim["value"])
        for side in (bundle["hospital"], bundle["payer"])
        for claim in side["claims"]
    }
    assert sent and reviewed == sent


def test_each_node_reads_only_its_own_file() -> None:
    federation = Federation()
    Chat(federation).send("Verify SYNTH-NPI-1999999999 for SYNTH-NETWORK-X")

    for role in ROLES:
        other = next(r for r in ROLES if r != role)
        assert role in federation.files_read[role]
        assert other not in federation.files_read[role]


@pytest.mark.parametrize("silent", ROLES)
def test_a_silent_node_cannot_be_approved_into_a_credential(silent: str) -> None:
    chat = Chat(Federation(offline=(silent,)))

    chat.send("Verify SYNTH-NPI-1999999999 for SYNTH-NETWORK-X")
    chat.send("/approve run-100")

    result = chat.record()["result"]
    assert result["outcome"] == "failed"
    assert silent in result["missing_nodes"]
    # An approve always leaves a receipt; it must record the failure.
    assert result["receipt"]["outcome"] == "failed"


@pytest.mark.parametrize("decision", ["escalate", "reject"])
def test_other_decisions_never_issue_a_receipt(decision: str) -> None:
    chat = Chat(Federation())

    chat.send("Verify SYNTH-NPI-1999999999 for SYNTH-NETWORK-X")
    chat.send(f"/{decision} run-100 needs a second look")

    assert not chat.record()["result"]["receipt"]
