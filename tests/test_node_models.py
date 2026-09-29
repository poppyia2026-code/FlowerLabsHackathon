"""Each SuperNode may word its notes with its own model; answers stay rule-based."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from poppy_orchestrator.supernodes import wording
from poppy_orchestrator.supernodes.wording import MAX_CHARS, word_note, word_reply
from tests.test_same_fab_round_trip import Chat, Federation

pytest.importorskip("flwr.app")

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas/claim_contract.schema.json").read_text())
NEBIUS = "dedicated/flowerai/MiniMax-M3-OOLI9o"
EXPLAINED = "SYNTH-NPI-1777777777"
NOTE = "Documented leave 2021-03 to 2021-10, employment continuous"
REWRITE = "The hospital has documented leave from 2021-03 to 2021-10 with continuous employment."


def says(text):
    return lambda note, instructions: text


def test_no_model_configured_keeps_the_fixed_text() -> None:
    result = word_note(NOTE, model_id=None, complete=says(REWRITE))

    assert (result.text, result.model) == (NOTE, None)


def test_a_good_rewrite_is_used_and_attributed() -> None:
    result = word_note(NOTE, model_id=NEBIUS, complete=says(REWRITE))

    assert (result.text, result.model) == (REWRITE, NEBIUS)


@pytest.mark.parametrize(
    "answer",
    [
        None,
        "",
        "   ",
        "x" * (MAX_CHARS + 1),
        "The hospital has documented leave, employment continuous.",
        "Documented leave 2021-03 to 2021-11, employment continuous",
    ],
    ids=["nothing", "empty", "blank", "too long", "dates dropped", "date changed"],
)
def test_a_bad_rewrite_keeps_the_fixed_text(answer) -> None:
    result = word_note(NOTE, model_id=NEBIUS, complete=says(answer))

    assert (result.text, result.model) == (NOTE, None)


def test_a_failing_model_keeps_the_fixed_text() -> None:
    def broken(note, instructions):
        raise TimeoutError("provider did not answer")

    result = word_note(NOTE, model_id=NEBIUS, complete=broken)

    assert (result.text, result.model) == (NOTE, None)


def test_model_without_credentials_keeps_the_fixed_text(monkeypatch) -> None:
    for name in ("FLWR_RUNTIME_BASE_URL", "FLWR_RUNTIME_API_KEY", "ENDEAVOR_API_KEY"):
        monkeypatch.delenv(name, raising=False)

    result = word_note(NOTE, model_id=NEBIUS)

    assert (result.text, result.model) == (NOTE, None)


def test_the_model_only_sees_text_that_was_already_leaving() -> None:
    seen: list[str] = []

    def record(note, instructions):
        seen.append(note)
        return REWRITE

    reply = {
        "ok": True,
        "provider_id": EXPLAINED,
        "claims": [
            {
                "claim_type": "work_history_complete",
                "value": True,
                "confidence": 0.95,
                "evidence_ref": "fixture://hospital/leave#R",
                "notes": NOTE,
                "resolves_dispute": True,
            }
        ],
    }

    word_reply(reply, model_id=NEBIUS, role="HospitalCred", is_recheck=True, complete=record)

    assert seen == [NOTE]


def test_typed_answers_are_never_touched() -> None:
    claim = {
        "claim_type": "work_history_complete",
        "value": True,
        "confidence": 0.95,
        "evidence_ref": "fixture://hospital/leave#R",
        "notes": NOTE,
        "resolves_dispute": True,
    }
    before = {k: v for k, v in claim.items() if k != "notes"}

    reply = word_reply(
        {"ok": True, "claims": [claim]},
        model_id=NEBIUS,
        role="HospitalCred",
        is_recheck=True,
        complete=says(REWRITE),
    )

    after = reply["claims"][0]
    assert {k: after[k] for k in before} == before
    assert after["notes"] == REWRITE
    assert after["worded_by"] == NEBIUS


def test_a_failed_reply_is_not_worded() -> None:
    reply = {"ok": False, "error": "unknown synthetic provider", "claims": []}

    assert word_reply(
        dict(reply), model_id=NEBIUS, role="HospitalCred", is_recheck=True,
        complete=says(REWRITE),
    ) == reply


def test_ordinary_claim_notes_are_left_alone() -> None:
    calls: list[str] = []

    def record(note, instructions):
        calls.append(note)
        return REWRITE

    reply = {
        "ok": True,
        "claims": [{"claim_type": "license_active", "value": True, "notes": "Synth"}],
    }

    word_reply(reply, model_id=NEBIUS, role="PayerEnrollment", is_recheck=False, complete=record)

    assert calls == []
    assert "worded_by" not in reply["claims"][0]


def test_reviewer_sees_which_model_worded_each_side(monkeypatch) -> None:
    monkeypatch.setattr(
        wording,
        "_complete_with_runtime",
        lambda model_id, role: lambda note, instructions: f"[{role}] {note}",
    )
    federation = Federation(
        models={"HospitalCred": NEBIUS, "PayerEnrollment": "flower/endeavor"}
    )
    chat = Chat(federation)

    chat.send(f"Verify {EXPLAINED} for SYNTH-NETWORK-X")

    text = chat.text()
    assert f"_(worded by {NEBIUS})_" in text
    assert "_(worded by flower/endeavor)_" in text
    assert "[HospitalCred] Documented leave" in text
    conflict = chat.record()["bundle"]["conflicts"][0]
    assert conflict["status"] == "explained"
    assert conflict["follow_up"]["worded_by"] == NEBIUS
    assert conflict["dispute"]["worded_by"] == "flower/endeavor"


def test_a_node_without_a_model_sends_the_fixed_text(monkeypatch) -> None:
    monkeypatch.setattr(
        wording,
        "_complete_with_runtime",
        lambda model_id, role: lambda note, instructions: f"[{role}] {note}",
    )
    chat = Chat(Federation(models={"HospitalCred": NEBIUS}))

    chat.send(f"Verify {EXPLAINED} for SYNTH-NETWORK-X")

    conflict = chat.record()["bundle"]["conflicts"][0]
    assert conflict["follow_up"]["worded_by"] == NEBIUS
    assert "worded_by" not in conflict["dispute"]


def test_worded_reply_matches_the_contract() -> None:
    reply = {
        "request_id": "recheck-1",
        "source_node": "HospitalCred",
        "provider_id": EXPLAINED,
        "claims": [
            {
                "claim_type": "work_history_complete",
                "value": True,
                "confidence": 0.95,
                "evidence_ref": "fixture://hospital/leave#R",
                "notes": REWRITE,
                "resolves_dispute": True,
                "worded_by": NEBIUS,
            }
        ],
        "ok": True,
        "error": None,
        "responded_at": 1.0,
        "synthetic": True,
    }

    jsonschema.validate(
        instance=reply,
        schema={"$ref": "#/definitions/claim_response", "definitions": SCHEMA["definitions"]},
    )
