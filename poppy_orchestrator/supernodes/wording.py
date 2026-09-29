"""Let a SuperNode's own model word the text it is about to send.

Which model and which provider is that organization's choice: the model id
comes from the node's `poppy-model` setting and the provider from the
SuperNode's own `FLWR_MODEL_API_*` environment.

The model is handed only text that was already cleared to leave the node, so
it cannot add anything the node did not intend to share. Typed answers
(`value`, `resolves_dispute`, `observed`) never come from the model. Any
failure keeps the fixed text.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, replace
from typing import Any, Callable, Optional

from poppy_orchestrator.endeavor.client import EndeavorClient
from poppy_orchestrator.endeavor.config import ENDEAVOR_MODEL_ID, resolve_endeavor_config

MAX_CHARS = 240
TIMEOUT_SECONDS = 15.0
INSTRUCTIONS = (
    "Rewrite the note as one plain sentence for a human reviewer. "
    "Keep every fact, date and number exactly. Add nothing. No preamble."
)

Completer = Callable[[str, str], Optional[str]]


@dataclass(frozen=True)
class Wording:
    text: str
    model: Optional[str]  # None when the fixed text was kept


def _complete_with_runtime(model_id: str, role: str) -> Completer:
    def complete(note: str, instructions: str) -> Optional[str]:
        config = resolve_endeavor_config({**os.environ, ENDEAVOR_MODEL_ID: model_id})
        result = EndeavorClient(replace(config, role=role)).complete(
            prompt=note, instructions=instructions, timeout_s=TIMEOUT_SECONDS
        )
        return result.text if result.live_call else None

    return complete


def _facts(text: str) -> set[str]:
    """Dates and numbers: the parts of a note a rewrite must not change."""
    return set(re.findall(r"\d+(?:[-/.]\d+)*", text))


def word_note(
    note: str,
    *,
    model_id: Optional[str],
    role: str = "SuperNode",
    complete: Optional[Completer] = None,
) -> Wording:
    if not model_id or not note.strip():
        return Wording(note, None)
    try:
        answer = (complete or _complete_with_runtime(model_id, role))(note, INSTRUCTIONS)
    except Exception:  # noqa: BLE001 - wording is optional, the reply is not
        return Wording(note, None)
    text = " ".join((answer or "").split())
    if not text or len(text) > MAX_CHARS or not _facts(note) <= _facts(text):
        return Wording(note, None)
    return Wording(text, model_id)


def word_reply(
    reply: dict[str, Any],
    *,
    model_id: Optional[str],
    role: str,
    is_recheck: bool,
    complete: Optional[Completer] = None,
) -> dict[str, Any]:
    """Word the one free-text field a person will read in this reply.

    A follow-up answer: the note on its single claim. A first answer: the
    reason on each dispute. Ordinary claim notes are left as they are.
    """
    if not model_id or reply.get("ok") is not True:
        return reply
    targets = (
        [(claim, "notes") for claim in reply.get("claims", [])[:1]]
        if is_recheck
        else [(dispute, "reason") for dispute in reply.get("disputes", [])]
    )
    for item, field in targets:
        wording = word_note(
            str(item.get(field) or ""), model_id=model_id, role=role, complete=complete
        )
        if wording.model:
            item[field] = wording.text
            item["worded_by"] = wording.model
    return reply
