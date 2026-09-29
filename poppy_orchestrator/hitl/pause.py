"""HITL pause stub for PoppyOrchestrator (F5 / F7 interface).

Orchestrator MUST pause before final credentialed status.
Franco owns the claim panel UI (Approve / Escalate / Reject).

Contract for Franco:
  1. Orchestrator emits `privcred.hitl.request` with ClaimBundle.to_dict()
  2. Franco UI / Flower Chat surfaces Approve | Escalate | Reject
  3. Decision arrives via HitlGate.wait_for_decision(...) → HitlDecision
  4. Orchestrator never auto-skips this gate on the live path

# F7: PanelHitlGate / ConsoleHitlGate / HttpPanelServer wire Approve|Escalate|Reject.
# F8 receipt emit lives in poppy_orchestrator.receipts.emit (after Approve only).
# Optional: Flower Chat connector can still wrap CallbackHitlGate.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, Optional
import time

from poppy_orchestrator.contracts.claims import (
    ClaimBundle,
    HitlAction,
    HitlDecision,
)
from poppy_orchestrator.events.emit import EventEmitter, emit_text


class HitlGate(ABC):
    """Pause point before credentialed / verification-complete outcome."""

    @abstractmethod
    def wait_for_decision(
        self,
        bundle: ClaimBundle,
        emitter: EventEmitter,
        *,
        timeout_s: Optional[float] = None,
    ) -> HitlDecision:
        raise NotImplementedError


def _emit_hitl_request(emitter: EventEmitter, bundle: ClaimBundle) -> None:
    emitter.emit(
        {
            "event": "privcred.hitl.request",
            "data": {
                "prompt": (
                    "HITL required: review aggregated verification claims, then "
                    "Approve / Escalate / Reject. Raw dossiers stay on SuperNodes."
                ),
                "actions": [a.value for a in HitlAction],
                "bundle": bundle.to_dict(),
                "synthetic": True,
            },
        }
    )
    emit_text(
        emitter,
        "HITL pause — waiting for human decision on claim panel "
        f"(provider={bundle.provider.provider_id}, "
        f"claims={len(bundle.all_claims())}, "
        f"missing={bundle.missing_nodes() or 'none'}).",
    )


class AutoApproveHitlGate(HitlGate):
    """Dry-run only — simulates judge Approve. NEVER use on live demo path."""

    def wait_for_decision(
        self,
        bundle: ClaimBundle,
        emitter: EventEmitter,
        *,
        timeout_s: Optional[float] = None,
    ) -> HitlDecision:
        _emit_hitl_request(emitter, bundle)
        decision = HitlDecision(
            action=HitlAction.APPROVE,
            actor="dry-run-auto",
            reason="Auto-approve for local dry-run (synthetic fixtures only)",
        )
        emitter.emit(
            {
                "event": "privcred.hitl.decision",
                "data": decision.to_dict(),
            }
        )
        emit_text(emitter, f"HITL decision (dry-run): {decision.action.value}")
        return decision


class ConsoleHitlGate(HitlGate):
    """Interactive CLI pause — F7 panel text; never auto-approves on empty input."""

    def wait_for_decision(
        self,
        bundle: ClaimBundle,
        emitter: EventEmitter,
        *,
        timeout_s: Optional[float] = None,
    ) -> HitlDecision:
        # Delegate to PanelHitlGate + console wait_fn (re-prompt, no default approve)
        from poppy_orchestrator.hitl.panel_gate import PanelHitlGate, console_panel_wait_fn

        _ = timeout_s
        gate = PanelHitlGate(wait_fn=console_panel_wait_fn(), actor="console-operator")
        return gate.wait_for_decision(bundle, emitter, timeout_s=timeout_s)


class CallbackHitlGate(HitlGate):
    """Production-facing interface for Franco's UI / Flower Chat callback.

    # TODO FRANCO: Pass a wait_fn that blocks until the claim panel posts a decision.
    # Example:
    #   gate = CallbackHitlGate(wait_fn=franco_ui.wait_for_hitl)
    # wait_fn(bundle_dict, timeout_s) -> {"action": "approve"|"escalate"|"reject", "actor": "...", "reason": "..."}
    """

    def __init__(
        self,
        wait_fn: Callable[[dict, Optional[float]], dict],
    ) -> None:
        self._wait_fn = wait_fn

    def wait_for_decision(
        self,
        bundle: ClaimBundle,
        emitter: EventEmitter,
        *,
        timeout_s: Optional[float] = None,
    ) -> HitlDecision:
        _emit_hitl_request(emitter, bundle)
        # TODO FRANCO: implement wait_fn — must not return until human acts
        raw = self._wait_fn(bundle.to_dict(), timeout_s)
        action = HitlAction(str(raw["action"]).lower())
        decision = HitlDecision(
            action=action,
            actor=str(raw.get("actor", "hitl-ui")),
            reason=str(raw.get("reason", "")),
            decided_at=float(raw.get("decided_at", time.time())),
        )
        emitter.emit({"event": "privcred.hitl.decision", "data": decision.to_dict()})
        return decision


# TODO FRANCO: FlowerChatHitlGate(HitlGate) — subscribe to chat/connector
# response after emitting privcred.hitl.request; map reply to HitlAction.
