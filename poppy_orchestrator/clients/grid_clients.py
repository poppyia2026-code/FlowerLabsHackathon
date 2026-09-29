"""Grid-backed SuperNode claim clients (FakeAgentGrid / live agent.grid).

Wires orchestrator claim fetch through the same F0 Grid handoff path
judges see (get_nodes → push → pull), then parses ClaimResponse JSON.

Fixture / FakeAgentGrid path needs no live SuperGrid. Leandro swaps in
live agent.grid once HospitalCred + PayerEnrollment SuperNodes are up.
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
from poppy_orchestrator.supernodes.claim_service import handle_inbound_message


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
    for node in data.get("nodes") or []:
        name = (node.get("name") or "").strip()
        if name.lower() == role.lower() or role.lower() in name.lower():
            return node
    return None


def fetch_claim_response_via_grid(
    grid: Any,
    role: str,
    request: ClaimRequest,
    *,
    pull_timeout: float = 0.0,
) -> ClaimResponse:
    """Push ClaimRequest-shaped payload to role node; pull ClaimResponse."""
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

    payload = json.dumps(
        {
            "from": "PoppyOrchestrator",
            "to": role,
            "intent": "request_verification_claims",
            "provider_id": request.provider.provider_id,
            "network_id": request.provider.network_id,
            "claim_types": list(request.claim_types),
            "request_id": request.request_id,
            "synthetic": True,
        },
        separators=(",", ":"),
    )
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
    if not messages:
        if isinstance(grid, FakeAgentGrid):
            # Local scaffold only: the fake grid has no real node to wait for.
            raw = handle_inbound_message(role, payload)
            return claim_response_from_dict(json.loads(raw))
        # Live grid: a missing reply is a missing node, never local data.
        return claim_response_from_grid_reply(role, request, None)

    return claim_response_from_grid_reply(role, request, messages[0])


def claim_response_from_grid_reply(
    role: str,
    request: ClaimRequest,
    reply: Optional[dict[str, Any]],
) -> ClaimResponse:
    """Turn one pulled Grid reply into a ClaimResponse (fail closed)."""

    def failed(reason: str) -> ClaimResponse:
        return ClaimResponse(
            request_id=request.request_id,
            source_node=role,
            provider_id=request.provider.provider_id,
            claims=(),
            ok=False,
            error=reason,
            synthetic=True,
        )

    if reply is None:
        return failed(f"no Grid reply from {role}")
    if reply.get("error"):
        return failed(f"{role} replied with an error: {reply['error']}")
    payload = reply.get("payload") or "{}"
    try:
        data = json.loads(payload) if isinstance(payload, str) else dict(payload)
        if data.get("ok") is False and "request_id" not in data:
            return failed(str(data.get("error") or f"{role} returned ok=false"))
        # Prefer request_id from orchestrator request for trace continuity.
        data["request_id"] = request.request_id
        response = claim_response_from_dict(data)
    except (json.JSONDecodeError, TypeError, KeyError, ValueError) as exc:
        return failed(f"invalid Grid claim reply: {exc}")
    if response.provider_id != request.provider.provider_id:
        return failed(
            f"{role} answered for provider {response.provider_id}, "
            f"expected {request.provider.provider_id}"
        )
    return response


class HandoffReplyClient(SuperNodeClaimClient):
    """Claims taken from the replies of the Grid handoff that already ran.

    Lets the credentialing flow use what the SuperNodes actually answered
    instead of contacting them a second time or reading local fixtures.
    """

    def __init__(self, role: str, reply: Optional[dict[str, Any]]) -> None:
        self.node_name = role
        self._reply = reply

    def request_claims(self, request: ClaimRequest) -> ClaimResponse:
        return claim_response_from_grid_reply(self.node_name, request, self._reply)


class GridHospitalCredClient(SuperNodeClaimClient):
    """HospitalCred claims via FakeAgentGrid / live agent.grid."""

    node_name = ROLE_HOSPITAL_CRED

    def __init__(self, grid: Any = None, *, pull_timeout: float = 0.0) -> None:
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

    def __init__(self, grid: Any = None, *, pull_timeout: float = 0.0) -> None:
        self._grid = grid if grid is not None else FakeAgentGrid()
        self._pull_timeout = pull_timeout

    def request_claims(self, request: ClaimRequest) -> ClaimResponse:
        return fetch_claim_response_via_grid(
            self._grid,
            ROLE_PAYER_ENROLLMENT,
            request,
            pull_timeout=self._pull_timeout,
        )
