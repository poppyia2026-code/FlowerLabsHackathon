"""Flower Chat shows what a reviewer needs; everything stays in the trace."""

from __future__ import annotations

import pytest

from poppy_orchestrator.events.emit import (
    AUDIENCE_TRACE,
    LocalEventBus,
    emit_text,
    flower_emitter_from_session,
)
from tests.test_same_fab_round_trip import Chat, Federation, StrictEvents

pytest.importorskip("flwr.app")

EXPLAINED = "SYNTH-NPI-1777777777"


class Session:
    def __init__(self) -> None:
        self.events = StrictEvents()


def shown(session: Session) -> str:
    return "".join(
        e["delta"] for e in session.events.items if e["type"] == "response.output_text.delta"
    )


def traced(chat_or_session) -> list[str]:
    return [
        e["data"]["text"]
        for e in chat_or_session.events.items
        if e["type"] == "privcred.message"
    ]


def test_reviewer_text_reaches_the_chat() -> None:
    session = Session()

    emit_text(flower_emitter_from_session(session), "Both sources agree.")

    assert shown(session) == "Both sources agree.\n\n"


def test_trace_text_stays_out_of_the_chat_but_in_the_trace() -> None:
    session = Session()

    emit_text(flower_emitter_from_session(session), "internal step", audience=AUDIENCE_TRACE)

    assert shown(session) == ""
    assert traced(session) == ["internal step"]


def test_preformatted_text_keeps_its_alignment_in_the_chat() -> None:
    session = Session()

    emit_text(flower_emitter_from_session(session), "a  b\nc  d", preformatted=True)

    assert shown(session) == "```text\na  b\nc  d\n```\n\n"


def test_local_console_output_is_unchanged() -> None:
    bus = LocalEventBus()

    emit_text(bus, "a  b", preformatted=True)

    assert bus.events[0]["data"]["text"] == "a  b"


def test_default_message_shape_is_unchanged() -> None:
    bus = LocalEventBus()

    emit_text(bus, "hello")

    assert bus.events[0]["data"] == {"role": "assistant", "text": "hello", "synthetic": True}


@pytest.mark.parametrize(
    "internal",
    ["PoppyOrchestrator kickoff", "HITL pause", "DRY-RUN", "NOT a live model call"],
)
def test_review_has_no_internal_lines(internal: str) -> None:
    chat = Chat(Federation())

    chat.send(f"Verify {EXPLAINED} for SYNTH-NETWORK-X")

    assert internal not in chat.text()
    assert any(internal in line for line in traced(chat))


def test_review_keeps_what_the_reviewer_needs() -> None:
    chat = Chat(Federation())

    chat.send(f"Verify {EXPLAINED} for SYNTH-NETWORK-X")

    text = chat.text()
    assert "Asking HospitalCred to look again" in text
    assert "HospitalCred looked again at work_history_complete: explained" in text
    assert "**Synthetic review run-100**" in text
    assert "/approve run-100" in text


def test_receipt_is_shown_as_one_aligned_block() -> None:
    chat = Chat(Federation())
    chat.send(f"Verify {EXPLAINED} for SYNTH-NETWORK-X")
    before = len(chat.text())

    chat.send("/approve run-100")

    decision = chat.text()[before:]
    assert decision.count("```text\n") == 1
    assert "AUDITABLE CLAIM RECEIPT" in decision
    assert "Synthetic review outcome: **credentialed**" in decision
