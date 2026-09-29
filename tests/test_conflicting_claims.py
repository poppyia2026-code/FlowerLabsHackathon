"""Two sources disagree on one claim: re-ask the owner once, then a person decides.

Provider R: the hospital's records account for the gap the payer sees.
Provider S: they do not, so the review cannot be approved.
"""

from __future__ import annotations

import pytest

from poppy_orchestrator.agent_app import kickoff_credentialing
from poppy_orchestrator.contracts.claims import (
    CONFLICT_AGREED,
    CONFLICT_EXPLAINED,
    CONFLICT_UNRESOLVED,
    ClaimConflict,
    ClaimDecision,
    ClaimDispute,
    CredentialingOutcome,
)
from poppy_orchestrator.events.emit import LocalEventBus
from poppy_orchestrator.hitl.pause import AutoApproveHitlGate
from tests.test_same_fab_round_trip import Chat, Federation

pytest.importorskip("flwr.app")

HAPPY = "SYNTH-NPI-1999999999"
EXPLAINED = "SYNTH-NPI-1777777777"
UNRESOLVED = "SYNTH-NPI-1666666666"
CLAIM = "work_history_complete"


def ask(provider_id: str) -> tuple[Chat, Federation]:
    federation = Federation()
    chat = Chat(federation)
    chat.send(f"Verify {provider_id} for SYNTH-NETWORK-X")
    return chat, federation


def dispute() -> ClaimDispute:
    return ClaimDispute(claim_type=CLAIM, observed=False, raised_by="PayerEnrollment")


def follow_up(value: bool, resolves: bool | None) -> ClaimDecision:
    return ClaimDecision(claim_type=CLAIM, value=value, resolves_dispute=resolves)


@pytest.mark.parametrize(
    ("answer", "status"),
    [
        (None, CONFLICT_UNRESOLVED),
        (follow_up(False, None), CONFLICT_AGREED),
        (follow_up(True, True), CONFLICT_EXPLAINED),
        (follow_up(True, False), CONFLICT_UNRESOLVED),
        (follow_up(True, None), CONFLICT_UNRESOLVED),
    ],
)
def test_status_comes_from_the_owners_second_answer(answer, status) -> None:
    conflict = ClaimConflict(
        claim_type=CLAIM,
        owner="HospitalCred",
        asserted=True,
        dispute=dispute(),
        follow_up=answer,
    )
    assert conflict.status == status


def test_agreeing_sources_need_no_second_round() -> None:
    chat, federation = ask(HAPPY)

    assert [role for role, _ in federation.deliveries] == [
        "HospitalCred",
        "PayerEnrollment",
    ]
    assert "conflicts" not in chat.record()["bundle"]
    assert "disagree" not in chat.text()


@pytest.mark.parametrize("provider_id", [EXPLAINED, UNRESOLVED])
def test_only_the_owner_is_asked_again_and_only_once(provider_id: str) -> None:
    _, federation = ask(provider_id)

    assert [role for role, _ in federation.deliveries] == [
        "HospitalCred",
        "PayerEnrollment",
        "HospitalCred",
    ]
    second = federation.deliveries[-1][1]
    assert second["claim_types"] == [CLAIM]
    assert second["recheck"]["period"] == "2021-03/2021-10"
    assert second["recheck"]["raised_by"] == "PayerEnrollment"


def test_payer_never_answers_the_claim_it_disputes() -> None:
    _, federation = ask(EXPLAINED)

    import json

    payer_reply = next(
        json.loads(reply["payload"])
        for reply in federation.replies.values()
        if json.loads(reply["payload"])["source_node"] == "PayerEnrollment"
    )
    assert CLAIM not in {c["claim_type"] for c in payer_reply["claims"]}
    assert payer_reply["disputes"][0]["claim_type"] == CLAIM


def test_explained_conflict_shows_both_sides_and_can_be_approved() -> None:
    chat, _ = ask(EXPLAINED)

    text = chat.text()
    assert f"Sources disagree on {CLAIM}: explained" in text
    assert "HospitalCred says: True" in text
    assert "PayerEnrollment sees: False for 2021-03/2021-10" in text
    assert "Documented leave" in text
    assert "/approve run-100" in text

    chat.send("/approve run-100")

    result = chat.record()["result"]
    assert result["outcome"] == "credentialed"
    assert result["receipt"]["outcome"] == "credentialed"


def test_unresolved_conflict_offers_no_approval() -> None:
    chat, _ = ask(UNRESOLVED)

    text = chat.text()
    assert f"Sources disagree on {CLAIM}: unresolved" in text
    assert "No record found" in text
    assert "/approve" not in text
    assert "/escalate run-100" in text


def test_approving_an_unresolved_conflict_applies_nothing() -> None:
    chat, _ = ask(UNRESOLVED)

    chat.send("/approve run-100")

    assert chat.record()["status"] == "pending"
    assert "approval is not available" in chat.text()

    chat.send("/escalate run-100 seven month gap")

    result = chat.record()["result"]
    assert result["outcome"] == "escalated"
    assert not result["receipt"]


def test_conflict_survives_between_chat_turns() -> None:
    chat, _ = ask(UNRESOLVED)

    saved = chat.record()["bundle"]["conflicts"]

    assert len(saved) == 1
    assert saved[0]["status"] == CONFLICT_UNRESOLVED
    assert saved[0]["follow_up"]["resolves_dispute"] is False


@pytest.mark.parametrize(
    ("provider_id", "outcome"),
    [
        (EXPLAINED, CredentialingOutcome.CREDENTIALED),
        (UNRESOLVED, CredentialingOutcome.FAILED),
    ],
)
def test_offline_path_fails_closed_on_an_unresolved_conflict(
    provider_id: str, outcome: CredentialingOutcome, monkeypatch
) -> None:
    monkeypatch.setenv("ENDEAVOR_ENABLED", "0")

    result = kickoff_credentialing(
        provider_id=provider_id,
        emitter=LocalEventBus(),
        hitl_gate=AutoApproveHitlGate(),
    )

    assert result.outcome == outcome
    assert len(result.bundle.conflicts) == 1
