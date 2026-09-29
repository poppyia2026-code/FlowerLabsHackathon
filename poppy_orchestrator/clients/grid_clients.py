"""Grid-backed SuperNode claim clients (FakeAgentGrid / live agent.grid).

Wires orchestrator claim fetch through the same F0 Grid handoff path
judges see (get_nodes → push → pull), then parses ClaimResponse JSON.

Offline tests can explicitly pass FakeAgentGrid. The AgentApp passes its real
agent.grid, and missing replies never fall back to local fixtures.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from poppy_orchestrator.clients.base import SuperNodeClaimClient
from poppy_orchestrator.contracts.claims import (
    ClaimRequest,
    ClaimResponse,
    claim_response_from_dict,
)
from poppy_orchestrator.grid.fake_grid import FakeAgentGrid
from poppy_orchestrator.grid.roles import ROLE_HOSPITAL_CRED, ROLE_PAYER_ENROLLMENT


def _find_node(grid: Any, role: str) -> Optional[dict[str, Any]]:
    out = grid.call(
        {
            "name": "get_nodes",
            "call_id": f"claim-fetch-{role}",
            "arguments": {"sample_size": None},
        }
    )
    raw = out.get("output", "{}")
    data = json.loads(raw) if isinstance(raw, str) else raw
    matches = []
    for node in data.get("nodes") or []:
        name = (node.get("name") or "").strip()
        if name.lower() == role.lower():
            matches.append(node)
    if len(matches) > 1:
        raise ValueError(f"Ambiguous Grid role: {role}")
    return matches[0] if matches else None


def fetch_claim_response_via_grid(
    grid: Any,
    role: str,
    request: ClaimRequest,
    *,
    pull_timeout: float = 30.0,
) -> ClaimResponse:
    """Push ClaimRequest-shaped payload to role node; pull ClaimResponse."""
    try:
        return _fetch_claim_response(grid, role, request, pull_timeout=pull_timeout)
    except (KeyError, TypeError, ValueError, RuntimeError, TimeoutError, OSError) as exc:
        return ClaimResponse(
            request_id=request.request_id,
            source_node=role,
            provider_id=request.provider.provider_id,
            claims=(),
            ok=False,
            error=f"Grid verification failed: {exc}",
            synthetic=True,
        )


def _fetch_claim_response(
    grid: Any, role: str, request: ClaimRequest, *, pull_timeout: float
) -> ClaimResponse:
    node = _find_node(grid, role)
    if node is None:
        return ClaimResponse(
            request_id=request.request_id,
            source_node=role,
            provider_id=request.provider.provider_id,
            claims=(),
            ok=False,
            error=f"Grid role not found: {role}",
            synthetic=True,
        )

    message: dict[str, Any] = {
        "from": "PoppyOrchestrator",
        "to": role,
        "intent": "request_verification_claims",
        "provider_id": request.provider.provider_id,
        "network_id": request.provider.network_id,
        "claim_types": list(request.claim_types),
        "request_id": request.request_id,
        "synthetic": True,
    }
    if request.recheck is not None:
        message["recheck"] = request.recheck.to_dict()
    payload = json.dumps(message, separators=(",", ":"))
    push = grid.call(
        {
            "name": "push_messages",
            "call_id": f"claim-push-{role}",
            "arguments": {
                "messages": [
                    {
                        "dst_node_id": str(node["id"]),
                        "payload": payload,
                        "reply_to_message_id": None,
                    }
                ]
            },
        }
    )
    push_out = json.loads(push["output"]) if isinstance(push["output"], str) else push["output"]
    results = push_out.get("results") or []
    if not results or not results[0].get("message_id"):
        return ClaimResponse(
            request_id=request.request_id,
            source_node=role,
            provider_id=request.provider.provider_id,
            claims=(),
            ok=False,
            error="Grid push_messages failed",
            synthetic=True,
        )
    mid = results[0]["message_id"]
    pull = grid.call(
        {
            "name": "pull_messages",
            "call_id": f"claim-pull-{role}",
            "arguments": {"message_ids": [mid], "timeout": pull_timeout},
        }
    )
    pull_out = json.loads(pull["output"]) if isinstance(pull["output"], str) else pull["output"]
    messages = pull_out.get("messages") or []
    if len(messages) != 1:
        raise ValueError("Expected one node reply; verification is pending or ambiguous")

    message = messages[0]
    if message.get("error"):
        raise ValueError(f"Node returned an error: {message['error']}")
    if message.get("reply_to_message_id") != mid:
        raise ValueError("Reply does not match the requested message")
    if str(message.get("src_node_id")) != str(node["id"]):
        raise ValueError("Reply came from a different node")

    reply_payload = messages[0].get("payload") or "{}"
    try:
        data = json.loads(reply_payload) if isinstance(reply_payload, str) else reply_payload
        if not isinstance(data, dict):
            raise ValueError("Reply must be a JSON object")
        if data.get("request_id") != request.request_id:
            raise ValueError("Reply request_id mismatch")
        if data.get("provider_id") != request.provider.provider_id:
            raise ValueError("Reply provider_id mismatch")
        if data.get("source_node") != role:
            raise ValueError("Reply role mismatch")
        if data.get("synthetic") is not True or not isinstance(data.get("ok"), bool):
            raise ValueError("Reply must declare boolean synthetic and ok fields")
        return claim_response_from_dict(data)
    except (json.JSONDecodeError, TypeError, KeyError, ValueError) as exc:
        return ClaimResponse(
            request_id=request.request_id,
            source_node=role,
            provider_id=request.provider.provider_id,
            claims=(),
            ok=False,
            error=f"invalid Grid claim reply: {exc}",
            synthetic=True,
        )


class GridHospitalCredClient(SuperNodeClaimClient):
    """HospitalCred claims via FakeAgentGrid / live agent.grid."""

    node_name = ROLE_HOSPITAL_CRED

    def __init__(self, grid: Any = None, *, pull_timeout: float = 30.0) -> None:
        self._grid = grid if grid is not None else FakeAgentGrid()
        self._pull_timeout = pull_timeout

    def request_claims(self, request: ClaimRequest) -> ClaimResponse:
        return fetch_claim_response_via_grid(
            self._grid,
            ROLE_HOSPITAL_CRED,
            request,
            pull_timeout=self._pull_timeout,
        )


class GridPayerEnrollmentClient(SuperNodeClaimClient):
    """PayerEnrollment claims via FakeAgentGrid / live agent.grid."""

    node_name = ROLE_PAYER_ENROLLMENT

    def __init__(self, grid: Any = None, *, pull_timeout: float = 30.0) -> None:
        self._grid = grid if grid is not None else FakeAgentGrid()
        self._pull_timeout = pull_timeout

    def request_claims(self, request: ClaimRequest) -> ClaimResponse:
        return fetch_claim_response_via_grid(
            self._grid,
            ROLE_PAYER_ENROLLMENT,
            request,
            pull_timeout=self._pull_timeout,
        )
