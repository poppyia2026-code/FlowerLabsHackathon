"""Event emission — works with AgentSession.events or local dry-run bus."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Protocol
import time
import uuid


# Who a text message is for. Everything is kept in the run trace; only
# reviewer messages are shown in Flower Chat.
AUDIENCE_REVIEWER = "reviewer"
AUDIENCE_TRACE = "trace"


class EventEmitter(Protocol):
    def emit(self, event: dict[str, Any]) -> None: ...


@dataclass
class LocalEventBus:
    """In-memory bus for dry-run / unit tests (no SuperGrid)."""

    events: list[dict[str, Any]] = field(default_factory=list)

    def emit(self, event: dict[str, Any]) -> None:
        envelope = {
            "id": f"evt-{uuid.uuid4().hex[:10]}",
            "timestamp": time.time(),
            **event,
        }
        self.events.append(envelope)
        et = event.get("event", "unknown")
        print(f"[event] {et}: {event.get('data', event)}")

    def get_trace(self) -> list[dict[str, Any]]:
        return list(self.events)


class NullEmitter:
    def emit(self, event: dict[str, Any]) -> None:
        return


def flower_emitter_from_session(agent: Any) -> EventEmitter:
    """Publish Flower 1.39 events and render human-readable messages in Chat."""
    events = getattr(agent, "events", None)
    if events is None:
        return NullEmitter()

    class _Adapter:
        def emit(self, event: dict[str, Any]) -> None:
            events.emit({**event, "type": event["event"]})
            if event["event"] != "privcred.message":
                return
            data = event["data"]
            if data.get("audience", AUDIENCE_REVIEWER) != AUDIENCE_REVIEWER:
                return
            text = data["text"]
            if data.get("preformatted"):
                text = f"```text\n{text}\n```"
            events.emit({"type": "response.output_text.delta", "delta": text + "\n\n"})

    return _Adapter()


def emit_text(
    emitter: EventEmitter,
    text: str,
    *,
    role: str = "assistant",
    audience: str = AUDIENCE_REVIEWER,
    preformatted: bool = False,
) -> None:
    """Publish human-readable text for Flower Chat / dry-run logs.

    ``audience=AUDIENCE_TRACE`` keeps a line out of the chat. ``preformatted``
    keeps the alignment of a fixed-width block when the chat renders it.
    """
    data: dict[str, Any] = {"role": role, "text": text, "synthetic": True}
    if audience != AUDIENCE_REVIEWER:
        data["audience"] = audience
    if preformatted:
        data["preformatted"] = True
    emitter.emit({"event": "privcred.message", "data": data})


def emit_stage(emitter: EventEmitter, stage: str, payload: Optional[dict] = None) -> None:
    emitter.emit(
        {
            "event": "privcred.stage",
            "data": {"stage": stage, "payload": payload or {}, "synthetic": True},
        }
    )
