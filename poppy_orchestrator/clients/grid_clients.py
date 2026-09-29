"""Grid-backed SuperNode claim clients (FakeAgentGrid / live agent.grid).

Wires orchestrator claim fetch through the same F0 Grid handoff path
judges see (get_nodes → push → pull), then parses ClaimResponse JSON.

Offline tests can explicitly pass FakeAgentGrid. The AgentApp passes its real
agent.grid, and missing replies never fall back to local fixtures.
"""

from __future__ import annotations

import json
import time
from typing import Any, Callable, Optional, Union

from poppy_orchestrator.clients.base import SuperNodeClaimClient
from poppy_orchestrator.contracts.claims import (
    ClaimRequest,
    ClaimResponse,
    claim_response_from_dict,
    new_request_id,
)
from poppy_orchestrator.grid.fake_grid import FakeAgentGrid
from poppy_orchestrator.grid.roles import ROLE_HOSPITAL_CRED, ROLE_PAYER_ENROLLMENT


class PullBudget:
    """One time allowance shared by every Grid wait in a run.

    SuperGrid stops a task five minutes after it starts. Each wait gets the
    per-message limit or whatever is left of the total, whichever is smaller,
    so a run with a follow-up round cannot wait its way past that limit.
    """

    def __init__(self, *, per_message: float, total: float) -> None:
        self._per_message = per_message
        self._deadline = time.monotonic() + total

    def __call__(self) -> float:
        remaining = self._deadline - time.monotonic()
        return max(0.0, min(self._per_message, remaining))


PullTimeout = Union[float, Callable[[], float]]


def _output(grid: Any, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    result = grid.call({"name": name, "call_id": new_request_id(f"claims-{name}"),
                        "arguments": arguments})
    data = result["output"]
    data = json.loads(data) if isinstance(data, str) else data
    if not isinstance(data, dict):
        raise ValueError(f"Invalid {name} output")
    return data


def _failure(role: str, request: ClaimRequest, error: str) -> ClaimResponse:
    return ClaimResponse(
        request_id=request.request_id,
        source_node=role,
        provider_id=request.provider.provider_id,
        claims=(), ok=False, error=error, synthetic=True,
    )


def _instruction(role: str, request: ClaimRequest) -> str:
    message: dict[str, Any] = {
        "from": "PoppyOrchestrator", "to": role,
        "intent": "request_verification_claims",
        "provider_id": request.provider.provider_id,
        "network_id": request.provider.network_id,
        "claim_types": list(request.claim_types),
        "request_id": request.request_id, "synthetic": True,
    }
    if request.recheck is not None:
        message["recheck"] = request.recheck.to_dict()
    return json.dumps(message, separators=(",", ":"))


def _read_reply(
    message: dict[str, Any], role: str, request: ClaimRequest, node_id: str,
) -> ClaimResponse:
    if message.get("error"):
        raise ValueError(f"Node returned an error: {message['error']}")
    if str(message.get("src_node_id")) != node_id:
        raise ValueError("Reply came from a different node")
    data = message.get("payload")
    data = json.loads(data) if isinstance(data, str) else data
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


_TRANSPORT_ERRORS = (KeyError, TypeError, ValueError, RuntimeError, TimeoutError, OSError)


def fetch_claim_responses_via_grid(
    grid: Any, requests: dict[str, ClaimRequest], *, pull_timeout: PullTimeout = 30.0,
) -> dict[str, ClaimResponse]:
    """Dispatch independent requests together, then correlate replies by message ID.

    The Grid client is used on one thread. Workers can execute concurrently;
    there is one node lookup, one push and one shared wait for the first round.
    Missing/invalid replies remain failures, while valid peers are preserved.
    """
    responses: dict[str, ClaimResponse] = {}
    if not requests:
        return responses
    try:
        nodes = _output(grid, "get_nodes", {"sample_size": None}).get("nodes")
        if not isinstance(nodes, list) or any(not isinstance(n, dict) for n in nodes):
            raise ValueError("Invalid Grid node list")
        selected: dict[str, str] = {}
        for role, request in requests.items():
            matches = [n for n in nodes if str(n.get("name") or "").strip().lower() == role.lower()]
            if len(matches) != 1 or not matches[0].get("id"):
                responses[role] = _failure(role, request, f"Grid role missing or ambiguous: {role}")
            else:
                selected[role] = str(matches[0]["id"])
        if len(set(selected.values())) != len(selected):
            raise ValueError("Distinct roles must resolve to distinct Grid nodes")
        if not selected:
            return responses

        roles = list(selected)
        pushed = _output(grid, "push_messages", {"messages": [
            {"dst_node_id": selected[role], "payload": _instruction(role, requests[role]),
             "reply_to_message_id": None}
            for role in roles
        ]}).get("results")
        # Flower returns push results in request order, but pull replies are unordered.
        if not isinstance(pushed, list) or len(pushed) != len(roles):
            raise ValueError("Grid returned an unexpected number of push results")
        accepted: dict[str, str] = {}
        for role, result in zip(roles, pushed):
            if not isinstance(result, dict):
                raise ValueError("Invalid Grid push result")
            mid = result.get("message_id")
            if result.get("error") or not isinstance(mid, str) or not mid:
                responses[role] = _failure(role, requests[role], "Grid push_messages failed")
            elif mid in accepted:
                raise ValueError("Grid returned duplicate message IDs")
            else:
                accepted[mid] = role
        if not accepted:
            return responses

        pulled = _output(grid, "pull_messages", {
            "message_ids": list(accepted),
            "timeout": pull_timeout() if callable(pull_timeout) else pull_timeout,
        })
        messages = pulled.get("messages")
        pending = pulled.get("pending_message_ids", [])
        if not isinstance(messages, list) or not isinstance(pending, list):
            raise ValueError("Invalid Grid pull result")
        by_id: dict[str, list[dict[str, Any]]] = {mid: [] for mid in accepted}
        for message in messages:
            if not isinstance(message, dict):
                raise ValueError("Invalid Grid reply")
            mid = message.get("reply_to_message_id")
            if not isinstance(mid, str) or mid not in accepted:
                raise ValueError("Reply does not match any requested message")
            by_id[mid].append(message)
        for mid, role in accepted.items():
            request = requests[role]
            try:
                if len(by_id[mid]) != 1 or mid in pending:
                    raise ValueError("Expected one node reply; verification is pending or ambiguous")
                responses[role] = _read_reply(by_id[mid][0], role, request, selected[role])
            except _TRANSPORT_ERRORS as exc:
                responses[role] = _failure(role, request, f"Grid verification failed: {exc}")
    except _TRANSPORT_ERRORS as exc:
        for role, request in requests.items():
            responses.setdefault(role, _failure(role, request, f"Grid verification failed: {exc}"))
    return responses


def fetch_claim_response_via_grid(
    grid: Any, role: str, request: ClaimRequest, *, pull_timeout: PullTimeout = 30.0,
) -> ClaimResponse:
    """Single-node follow-ups use the same validation and shared time budget."""
    return fetch_claim_responses_via_grid(
        grid, {role: request}, pull_timeout=pull_timeout,
    )[role]


class GridHospitalCredClient(SuperNodeClaimClient):
    """HospitalCred claims via FakeAgentGrid / live agent.grid."""

    node_name = ROLE_HOSPITAL_CRED

    def __init__(
        self, grid: Any = None, *, pull_timeout: PullTimeout = 30.0
    ) -> None:
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

    def __init__(
        self, grid: Any = None, *, pull_timeout: PullTimeout = 30.0
    ) -> None:
        self._grid = grid if grid is not None else FakeAgentGrid()
        self._pull_timeout = pull_timeout

    def request_claims(self, request: ClaimRequest) -> ClaimResponse:
        return fetch_claim_response_via_grid(
            self._grid,
            ROLE_PAYER_ENROLLMENT,
            request,
            pull_timeout=self._pull_timeout,
        )
