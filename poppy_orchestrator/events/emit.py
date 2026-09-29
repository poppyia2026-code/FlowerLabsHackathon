"""Event emission — works with AgentSession.events or local dry-run bus."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Protocol
import time
import uuid


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


def to_flower_event(event: dict[str, Any]) -> dict[str, Any]:
    """Shape a PrivCred envelope the way ``AgentSession.events.emit`` requires.

    The Flower runtime rejects any event without a non-empty string ``type``.
    Human-readable text goes out as a chat ``message`` so it shows up in
    Flower Chat; every other envelope keeps its name as the ``type``.
    """
    if isinstance(event.get("type"), str) and event["type"]:
        return event
    name = str(event.get("event") or "privcred.event")
    data = event.get("data") or {}
    if name == "privcred.message" and isinstance(data.get("text"), str):
        return {
            "type": "message",
            "role": str(data.get("role") or "assistant"),
            "content": data["text"],
        }
    return {"type": name, **event}


def flower_emitter_from_session(agent: Any) -> EventEmitter:
    """Adapt AgentSession.events to EventEmitter protocol."""
    events = getattr(agent, "events", None)
    if events is None:
        return NullEmitter()

    class _Adapter:
        def emit(self, event: dict[str, Any]) -> None:
            events.emit(to_flower_event(event))

    return _Adapter()


def emit_text(emitter: EventEmitter, text: str, *, role: str = "assistant") -> None:
    """Publish human-readable text for Flower Chat / dry-run logs."""
    emitter.emit(
        {
            "event": "privcred.message",
            "data": {"role": role, "text": text, "synthetic": True},
        }
    )


def emit_stage(emitter: EventEmitter, stage: str, payload: Optional[dict] = None) -> None:
    emitter.emit(
        {
            "event": "privcred.stage",
            "data": {"stage": stage, "payload": payload or {}, "synthetic": True},
        }
    )
