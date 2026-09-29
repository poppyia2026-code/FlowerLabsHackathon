"""Concurrent dispatch must preserve each institution's identity and failures."""
import copy
import json

import pytest

from poppy_orchestrator.clients.grid_clients import (
    fetch_claim_responses_via_grid,
)
from poppy_orchestrator.contracts.claims import (
    HOSPITAL_CRED_CLAIMS, PAYER_ENROLLMENT_CLAIMS, ClaimRequest, ProviderRef,
)
from poppy_orchestrator.grid.fake_grid import FakeAgentGrid, FakeGridNode
from tests.test_same_fab_round_trip import Chat, Federation, CoordinatorGrid


def requests():
    provider = ProviderRef("SYNTH-NPI-1999999999", "SYNTH-NETWORK-X")
    return {
        role: ClaimRequest(f"request-{role}", provider, tuple(sorted(claims)), role)
        for role, claims in (("HospitalCred", HOSPITAL_CRED_CLAIMS),
                             ("PayerEnrollment", PAYER_ENROLLMENT_CLAIMS))
    }


class ChangedReplies(FakeAgentGrid):
    def __init__(self, change):
        super().__init__()
        self.change = change

    def _pull_messages(self, message_ids, timeout=0):
        result = super()._pull_messages(message_ids, timeout)
        self.change(result)
        return result


def test_both_requests_are_dispatched_before_any_wait_and_keep_separate_claims():
    class Together(FakeAgentGrid):
        def _pull_messages(self, message_ids, timeout=0):
            assert len(self._pending) == len(message_ids) == 2
            return super()._pull_messages(message_ids, timeout)

    grid = Together()
    replies = fetch_claim_responses_via_grid(grid, requests())

    assert all(reply.ok for reply in replies.values())
    calls = [event for event in grid.events if event["type"] == "function_call"]
    assert [call["name"] for call in calls] == ["get_nodes", "push_messages", "pull_messages"]
    messages = json.loads(calls[1]["arguments"])["messages"]
    for message in messages:
        payload = json.loads(message["payload"])
        assert set(payload["claim_types"]) == set(requests()[payload["to"]].claim_types)
        assert "local_record" not in payload


def test_unordered_replies_are_associated_by_message_id():
    replies = fetch_claim_responses_via_grid(
        ChangedReplies(lambda result: result["messages"].reverse()), requests(),
    )
    for role, reply in replies.items():
        assert reply.ok
        assert reply.source_node == role
        assert reply.request_id == requests()[role].request_id


@pytest.mark.parametrize("change", [
    lambda result: result["messages"].pop(0),
    lambda result: result["messages"].append(copy.deepcopy(result["messages"][0])),
    lambda result: result["messages"][0].update(src_node_id="wrong-node"),
    lambda result: result["messages"][0].update(error="node failed"),
    lambda result: result["messages"][0].update(payload="not-json"),
    lambda result: result["messages"][0].update(payload="[]"),
    lambda result: result["pending_message_ids"].append(result["messages"][0]["reply_to_message_id"]),
])
def test_missing_ambiguous_or_invalid_reply_does_not_hide_healthy_peer(change):
    replies = fetch_claim_responses_via_grid(ChangedReplies(change), requests())
    assert not replies["HospitalCred"].ok
    assert replies["HospitalCred"].claims == ()
    assert replies["PayerEnrollment"].ok


@pytest.mark.parametrize(("field", "value"), [
    ("request_id", "other-request"), ("provider_id", "other-provider"),
    ("source_node", "PayerEnrollment"), ("synthetic", "true"), ("ok", "true"),
])
def test_corrupted_identity_in_one_payload_cannot_be_accepted(field, value):
    def change(result):
        message = result["messages"][0]
        data = json.loads(message["payload"])
        data[field] = value
        message["payload"] = json.dumps(data)
    replies = fetch_claim_responses_via_grid(ChangedReplies(change), requests())
    assert not replies["HospitalCred"].ok
    assert replies["PayerEnrollment"].ok


def test_unrequested_reply_is_rejected():
    grid = ChangedReplies(lambda result: result["messages"][0].update(reply_to_message_id="unknown"))
    assert not any(r.ok for r in fetch_claim_responses_via_grid(grid, requests()).values())


@pytest.mark.parametrize("fault", ["short", "duplicate", "partial", "error-with-id"])
def test_push_errors_never_assume_that_a_request_was_accepted(fault):
    class PushFault(FakeAgentGrid):
        def _push_messages(self, messages):
            result = super()._push_messages(messages)
            if fault == "short":
                result["results"].pop()
            elif fault == "duplicate":
                result["results"][1] = result["results"][0].copy()
            elif fault == "partial":
                result["results"][1] = {"message_id": None, "error": "offline"}
            else:
                result["results"][1]["error"] = "rejected"
            return result
    replies = fetch_claim_responses_via_grid(PushFault(), requests())
    assert not replies["PayerEnrollment"].ok
    assert replies["HospitalCred"].ok == (fault in {"partial", "error-with-id"})


def test_missing_role_still_collects_the_other_institution():
    grid = FakeAgentGrid(nodes=[FakeGridNode("11", "HospitalCred")])
    replies = fetch_claim_responses_via_grid(grid, requests())
    assert replies["HospitalCred"].ok
    assert not replies["PayerEnrollment"].ok


def test_one_node_cannot_impersonate_both_institutions():
    grid = FakeAgentGrid(nodes=[FakeGridNode("11", role) for role in requests()])
    assert not any(r.ok for r in fetch_claim_responses_via_grid(grid, requests()).values())
    assert not grid._pending


def test_live_chat_batches_first_round_then_rechecks_owner_with_remaining_budget(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr("poppy_orchestrator.clients.grid_clients.time.monotonic", lambda: now[0])
    class TimedGrid(CoordinatorGrid):
        batches = []
        waits = []

        def _push_messages(self, messages):
            self.batches.append(len(messages))
            return super()._push_messages(messages)

        def _pull_messages(self, message_ids, timeout):
            self.waits.append(timeout)
            result = super()._pull_messages(message_ids, timeout)
            now[0] += 230
            return result

    federation = Federation()
    chat = Chat(federation)
    chat.grid = TimedGrid(federation)
    chat.context.run_config.update({"grid-pull-timeout": 120, "grid-wait-budget": 240})
    chat.send("Verify SYNTH-NPI-1777777777 for SYNTH-NETWORK-X")

    assert chat.grid.batches == [2, 1]
    assert chat.grid.waits == [120, 10]
    assert chat.record()["status"] == "pending"
    assert chat.record()["bundle"]["conflicts"][0]["status"] == "explained"
    assert [role for role, _ in federation.deliveries] == ["HospitalCred", "PayerEnrollment", "HospitalCred"]
