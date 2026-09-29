"""Handle a real Flower instruction using only the configured local data shard."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from poppy_orchestrator.grid.roles import PRIVCRED_GRID_ROLES
from poppy_orchestrator.supernodes.claim_service import handle_inbound_message
from poppy_orchestrator.supernodes.wording import word_reply


def serve_runtime_instruction(agent: Any, context: Any, role: str | None = None) -> None:
    """A SuperNode replies to its instruction; it never starts orchestration."""
    node_config = context.node_config
    local_role = node_config.get("poppy-role")
    if local_role not in PRIVCRED_GRID_ROLES or (role and role != local_role):
        raise ValueError("Configure this SuperNode's poppy-role locally")
    data_path = node_config.get("poppy-data")
    if not isinstance(data_path, str) or not Path(data_path).is_file():
        raise ValueError("Configure poppy-data with this node's local synthetic shard")
    catalog = json.loads(Path(data_path).read_text())
    if catalog.get("meta", {}).get("synthetic") is not True:
        raise ValueError("This demo only accepts explicitly synthetic local data")

    # Flower 1.39 wraps Grid instructions in {message_id, src_node_id, payload}.
    envelope = json.loads(agent.prompt)
    if not isinstance(envelope, dict) or not envelope.get("message_id"):
        raise ValueError("Expected a Flower instruction envelope")
    payload = envelope.get("payload")
    data = json.loads(payload) if isinstance(payload, str) else payload
    if not isinstance(data, dict):
        raise ValueError("Expected a JSON claim request")
    if data.get("to") != local_role or data.get("synthetic") is not True:
        raise ValueError("Request does not match this node's role or synthetic scope")
    if data.get("intent") != "request_verification_claims":
        raise ValueError("Unsupported instruction")
    for field in ("provider_id", "network_id", "request_id"):
        if not isinstance(data.get(field), str) or not data[field]:
            raise ValueError(f"Missing {field}")
    if not isinstance(data.get("claim_types"), list) or not data["claim_types"]:
        raise ValueError("Explicit claim_types are required")

    reply = handle_inbound_message(local_role, data, fixtures_path=Path(data_path))
    model_id = node_config.get("poppy-model")
    if isinstance(model_id, str) and model_id:
        reply = json.dumps(
            word_reply(
                json.loads(reply),
                model_id=model_id,
                role=local_role,
                is_recheck=isinstance(data.get("recheck"), dict),
            ),
            separators=(",", ":"),
        )
    result = agent.grid.call({
        "name": "push_reply_message",
        "call_id": f"reply-{data['request_id']}",
        "arguments": {"payload": reply},
    })
    output = result.get("output", {})
    output = json.loads(output) if isinstance(output, str) else output
    if output.get("error") or not output.get("message_id"):
        raise RuntimeError("Flower did not accept the SuperNode reply")
