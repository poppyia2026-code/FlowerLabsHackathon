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


def flower_emitter_from_session(agent: Any) -> EventEmitter:
    """Adapt AgentSession.events to EventEmitter protocol.

    # TODO LEANDRO: confirm agent.events.emit accepts our PrivCred event envelopes
    # when wiring live SuperGrid. Flower Chat consumes published events.
    """
    events = getattr(agent, "events", None)
    if events is None:
        return NullEmitter()

    class _Adapter:
        def emit(self, event: dict[str, Any]) -> None:
            events.emit(event)

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
