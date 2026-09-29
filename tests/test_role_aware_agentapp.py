"""One FAB on SuperLink and SuperNodes: role awareness end to end.

The doubles below copy the behaviour of Flower's runtime that the app
depends on (flwr 1.39): a different Grid tool set per side, an instruction
delivered as ``agent.prompt``, one reply per instruction, and events that
must carry a string ``type``.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Optional

import pytest

from poppy_orchestrator import agent_app
from poppy_orchestrator.events.emit import to_flower_event
from poppy_orchestrator.grid.handoff import assign_roles
from poppy_orchestrator.grid.roles import (
    PRIVCRED_GRID_ROLES,
    ROLE_HOSPITAL_CRED,
    ROLE_PAYER_ENROLLMENT,
)
from poppy_orchestrator.supernodes.node_runtime import (
    build_reply,
    is_supernode_session,
)

SUPERLINK_TOOLS = {"get_nodes", "push_messages", "pull_messages"}
SUPERNODE_TOOLS = {"push_reply_message"}
SUPERLINK_NODE_ID = "1"
PROVIDER = "SYNTH-NPI-1999999999"


class StrictEvents:
    """Rejects what ``RuntimeAgentEvents.emit`` rejects."""

    def __init__(self) -> None:
        self.items: list[dict[str, Any]] = []

    def emit(self, event: dict[str, Any]) -> None:
        event_type = event.get("type")
        if not isinstance(event_type, str) or not event_type:
            raise ValueError("Run event requires a non-empty string 'type' field.")
        self.items.append(event)

    def get_trace(self) -> list[dict[str, Any]]:
        return []


class Context:
    def __init__(self, run_config: Optional[dict[str, str]] = None) -> None:
        self.run_config = run_config or {}
        self.run_id = "run-test"
        self.state: dict[str, Any] = {}


class Session:
    def __init__(self, prompt: str, grid: Any) -> None:
        self.prompt = prompt
        self.grid = grid
        self.events = StrictEvents()


class ToolGrid:
    names: set[str] = set()

    def tools(self) -> list[dict[str, Any]]:
        return [{"type": "function", "name": name} for name in sorted(self.names)]

    def call(self, tool_call: dict[str, Any]) -> dict[str, Any]:
        name = tool_call["name"]
        if name not in self.names:
            raise ValueError(f"Unsupported Grid tool '{name}'.")
        output = getattr(self, f"_{name}")(**tool_call["arguments"])
        return {
            "type": "function_call_output",
            "call_id": tool_call["call_id"],
            "output": json.dumps(output),
        }


class Federation:
    """A SuperLink plus SuperNodes that all run ``agent_app.main``."""

    def __init__(
        self,
        nodes: list[dict[str, Any]],
        *,
        reply_transform: Optional[Callable[[str], str]] = None,
        failing_node_ids: tuple[str, ...] = (),
    ) -> None:
        self.nodes = nodes
        self.reply_transform = reply_transform
        self.failing_node_ids = failing_node_ids
        self.replies: dict[str, dict[str, Any]] = {}
        self.node_prompts: list[str] = []
        self._count = 0

    def next_id(self) -> str:
        self._count += 1
        return f"msg-{self._count}"

    def deliver(self, node_id: str, message_id: str, payload: str) -> None:
        if node_id in self.failing_node_ids:
            return
        prompt = json.dumps(
            {
                "message_id": message_id,
                "src_node_id": SUPERLINK_NODE_ID,
                "payload": payload,
            }
        )
        self.node_prompts.append(prompt)
        session = Session(prompt, SuperNodeGrid(self, node_id, message_id))
        agent_app.main(session, Context())


class SuperLinkGrid(ToolGrid):
    names = SUPERLINK_TOOLS

    def __init__(self, federation: Federation) -> None:
        self.federation = federation

    def _get_nodes(self, sample_size: Optional[int]) -> dict[str, Any]:
        nodes = self.federation.nodes
        selected = nodes if sample_size is None else nodes[:sample_size]
        return {"nodes": selected, "num_available": len(nodes)}

    def _push_messages(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        results = []
        for message in messages:
            message_id = self.federation.next_id()
            self.federation.deliver(
                message["dst_node_id"], message_id, message["payload"]
            )
            results.append({"message_id": message_id, "error": None})
        return {"results": results}

    def _pull_messages(self, message_ids: list[str], timeout: float) -> dict[str, Any]:
        found = [
            self.federation.replies[mid]
            for mid in message_ids
            if mid in self.federation.replies
        ]
        pending = [mid for mid in message_ids if mid not in self.federation.replies]
        return {"messages": found, "pending_message_ids": pending}


class SuperNodeGrid(ToolGrid):
    names = SUPERNODE_TOOLS

    def __init__(self, federation: Federation, node_id: str, message_id: str) -> None:
        self.federation = federation
        self.node_id = node_id
        self.message_id: Optional[str] = message_id

    def _push_reply_message(self, payload: str) -> dict[str, Any]:
        if self.message_id is None:
            return {"message_id": None, "error": "No instruction message to reply to."}
        transform = self.federation.reply_transform
        reply_id = self.federation.next_id()
        self.federation.replies[self.message_id] = {
            "message_id": reply_id,
            "reply_to_message_id": self.message_id,
            "src_node_id": self.node_id,
            "payload": transform(payload) if transform else payload,
            "error": None,
        }
        self.message_id = None
        return {"message_id": reply_id, "error": None}


def node(node_id: str, name: Optional[str] = None) -> dict[str, Any]:
    return {"id": node_id, "name": name, "location": None}


def run_orchestrator(federation: Federation) -> tuple[Session, Context]:
    session = Session("Credential synthetic provider", SuperLinkGrid(federation))
    context = Context({"hitl-auto-approve-dry-run": "true"})
    agent_app.main(session, context)
    return session, context


def stage_payload(session: Session, stage: str) -> dict[str, Any]:
    for event in session.events.items:
        data = event.get("data") or {}
        if data.get("stage") == stage:
            return data["payload"]
    raise AssertionError(f"stage {stage} was never emitted")


def test_doubles_match_flwr_tool_names() -> None:
    grid = pytest.importorskip("flwr.supercore.task_process.agent.grid")
    assert grid._GRID_TOOL_NAMES == SUPERLINK_TOOLS
    assert grid._SUPERNODE_GRID_TOOL_NAMES == SUPERNODE_TOOLS


def test_session_side_is_read_from_the_grid_tools() -> None:
    federation = Federation([node("11"), node("12")])
    assert not is_supernode_session(Session("", SuperLinkGrid(federation)))
    assert is_supernode_session(Session("", SuperNodeGrid(federation, "11", "msg-0")))


def test_roles_are_assigned_to_unnamed_nodes() -> None:
    assigned, missing = assign_roles([node("12"), node("11")], PRIVCRED_GRID_ROLES)
    assert missing == []
    assert {n["id"] for n in assigned.values()} == {"11", "12"}


def test_named_node_keeps_its_role() -> None:
    nodes = [node("11", "Lakeside Medical Center"), node("12", "PayerEnrollment West")]
    assigned, _ = assign_roles(nodes, PRIVCRED_GRID_ROLES)
    assert assigned[ROLE_PAYER_ENROLLMENT]["id"] == "12"
    assert assigned[ROLE_HOSPITAL_CRED]["id"] == "11"


def test_one_node_is_not_enough_for_two_roles() -> None:
    _, missing = assign_roles([node("11")], PRIVCRED_GRID_ROLES)
    assert missing == [ROLE_PAYER_ENROLLMENT]


def test_full_run_with_unnamed_nodes_credentials_the_provider() -> None:
    federation = Federation([node("11"), node("12")])
    _, context = run_orchestrator(federation)

    assert context.state["privcred_outcome"] == "credentialed"
    assert len(federation.node_prompts) == 2
    assert len(federation.replies) == 2


def test_each_node_answers_only_its_own_claims() -> None:
    federation = Federation([node("11"), node("12")])
    run_orchestrator(federation)

    by_role = {}
    for reply in federation.replies.values():
        body = json.loads(reply["payload"])
        by_role[body["source_node"]] = {c["claim_type"] for c in body["claims"]}
    assert set(by_role) == {ROLE_HOSPITAL_CRED, ROLE_PAYER_ENROLLMENT}
    assert "work_history_complete" in by_role[ROLE_HOSPITAL_CRED]
    assert "license_active" in by_role[ROLE_PAYER_ENROLLMENT]
    assert not by_role[ROLE_HOSPITAL_CRED] & by_role[ROLE_PAYER_ENROLLMENT]


def test_flow_uses_what_the_nodes_answered() -> None:
    def mark(payload: str) -> str:
        body = json.loads(payload)
        for claim in body["claims"]:
            claim["notes"] = "answered-by-supernode"
        return json.dumps(body)

    federation = Federation([node("11"), node("12")], reply_transform=mark)
    session, _ = run_orchestrator(federation)

    for role in PRIVCRED_GRID_ROLES:
        claims = stage_payload(session, f"claim_response.{role}")["claims"]
        assert claims
        assert {c["notes"] for c in claims} == {"answered-by-supernode"}


def test_silent_node_fails_the_run_instead_of_using_local_data() -> None:
    federation = Federation([node("11"), node("12")], failing_node_ids=("12",))
    with pytest.raises(RuntimeError, match="Grid handoff failed"):
        run_orchestrator(federation)


def test_node_rejects_a_request_for_an_unknown_role() -> None:
    prompt = json.dumps(
        {
            "message_id": "msg-1",
            "src_node_id": SUPERLINK_NODE_ID,
            "payload": json.dumps({"to": "Pharmacy", "provider_id": PROVIDER}),
        }
    )
    _, reply = build_reply(prompt)
    body = json.loads(reply)
    assert body["ok"] is False
    assert "Pharmacy" in body["error"]


def test_every_emitted_event_has_a_type() -> None:
    # StrictEvents raises on a missing type, so reaching the end is the proof.
    session, _ = run_orchestrator(Federation([node("11"), node("12")]))
    assert session.events.items
    assert any(e["type"] == "message" for e in session.events.items)


def test_text_is_published_as_a_chat_message() -> None:
    event = to_flower_event(
        {"event": "privcred.message", "data": {"role": "assistant", "text": "hi"}}
    )
    assert event == {"type": "message", "role": "assistant", "content": "hi"}
