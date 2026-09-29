"""Flower AgentApp entrypoint for PoppyOrchestrator (F5).

AgentApp-only FAB (see pyproject.toml [tool.flwr.app.components]).
Do NOT add ServerApp/ClientApp to this bundle.

Live path requires SuperGrid credentials + Leandro SuperNodes + Franco HITL.
Local dry-run / CLI:
  python -m poppy_orchestrator
  python scripts/run_f5.py
  python scripts/dry_run.py
"""

from __future__ import annotations

from typing import Any, Optional

from poppy_orchestrator.clients.base import SuperNodeClaimClient
from poppy_orchestrator.clients.hospital_cred import StubHospitalCredClient
from poppy_orchestrator.clients.payer_enrollment import StubPayerEnrollmentClient
from poppy_orchestrator.events.emit import EventEmitter, flower_emitter_from_session
from poppy_orchestrator.hitl.pause import (
    AutoApproveHitlGate,
    ConsoleHitlGate,
    HitlGate,
)
from poppy_orchestrator.orchestration.flow import (
    FlowResult,
    OrchestratorConfig,
    run_credentialing_flow,
)

# ---------------------------------------------------------------------------
# Flower AgentApp registration (best-effort if flwr.agentapp is available)
# Official import: from flwr.agentapp import AgentApp, AgentSession
# ---------------------------------------------------------------------------
try:
    from flwr.agentapp import AgentApp  # type: ignore
except ImportError:  # pragma: no cover
    try:
        from flwr.agent import AgentApp  # type: ignore
    except ImportError:  # pragma: no cover
        AgentApp = None  # type: ignore


def _build_app() -> Any:
    if AgentApp is None:
        # Placeholder so `from poppy_orchestrator.agent_app import app` works
        # for dry-run / unit import without flwr installed.
        class _StubApp:
            """flwr not installed — use python -m poppy_orchestrator locally."""

            def main(self):  # decorator no-op
                def deco(fn):
                    return fn

                return deco

        return _StubApp()
    return AgentApp()


app = _build_app()


def build_stub_clients() -> tuple[SuperNodeClaimClient, SuperNodeClaimClient]:
    """Synthetic SuperNode stubs (fixtures/providers.json)."""
    return StubHospitalCredClient(), StubPayerEnrollmentClient()


def build_hitl_gate(*, mode: str = "auto") -> HitlGate:
    """HITL gate for local / AgentApp paths.

    Modes: auto | approve (alias) | console.
    Live demo must use Franco CallbackHitlGate — never silent skip.
    """
    normalized = (mode or "auto").lower()
    if normalized in {"console", "cli"}:
        return ConsoleHitlGate()
    # auto / approve — dry-run AutoApprove still emits privcred.hitl.request
    return AutoApproveHitlGate()


def kickoff_credentialing(
    *,
    provider_id: str = "SYNTH-NPI-1999999999",
    network_id: str = "SYNTH-NETWORK-X",
    display_name: str = "",
    run_id: Optional[str] = None,
    emitter: Optional[EventEmitter] = None,
    hitl_gate: Optional[HitlGate] = None,
    hospital: Optional[SuperNodeClaimClient] = None,
    payer: Optional[SuperNodeClaimClient] = None,
    fixture_mode: bool = True,
) -> FlowResult:
    """F5 kickoff entry: credential provider P for network X.

    Shared by AgentApp main, ``python -m poppy_orchestrator``, and scripts.
    Synthetic fixtures only unless Leandro wires real SuperNode clients.
    """
    if not fixture_mode:
        raise RuntimeError(
            "fixture-mode=false but RealHospitalCredClient / RealPayerEnrollmentClient "
            "are not wired yet. TODO LEANDRO: implement and switch here."
        )

    if hospital is None or payer is None:
        hospital, payer = build_stub_clients()
    if hitl_gate is None:
        hitl_gate = build_hitl_gate(mode="auto")
    if emitter is None:
        from poppy_orchestrator.events.emit import LocalEventBus

        emitter = LocalEventBus()

    config = OrchestratorConfig(
        provider_id=provider_id,
        network_id=network_id,
        display_name=display_name,
        run_id=run_id,
    )
    return run_credentialing_flow(
        hospital=hospital,
        payer=payer,
        hitl_gate=hitl_gate,
        emitter=emitter,
        config=config,
    )


@app.main()
def main(agent: Any, context: Any) -> None:
    """AgentApp main — invoked by Flower SuperGrid / SuperLink runtime."""
    run_config = getattr(context, "run_config", {}) or {}
    # Flower run_config values are often strings
    provider_id = str(run_config.get("provider-id", "SYNTH-NPI-1999999999"))
    network_id = str(run_config.get("network-id", "SYNTH-NETWORK-X"))
    fixture_mode = str(run_config.get("fixture-mode", "true")).lower() in {
        "1",
        "true",
        "yes",
    }
    auto_hitl = str(run_config.get("hitl-auto-approve-dry-run", "false")).lower() in {
        "1",
        "true",
        "yes",
    }
    run_id = str(getattr(context, "run_id", "") or "") or None

    emitter = flower_emitter_from_session(agent)

    # --- SuperNode clients ---
    # TODO LEANDRO: when fixture_mode is false, swap stubs for Real* clients
    # wired to agent.connectors / federation SuperNodes HospitalCred + PayerEnrollment.
    if not fixture_mode:
        raise RuntimeError(
            "fixture-mode=false but RealHospitalCredClient / RealPayerEnrollmentClient "
            "are not wired yet. TODO LEANDRO: implement and switch here."
        )
    hospital, payer = build_stub_clients()

    # --- HITL gate ---
    # TODO FRANCO: replace with CallbackHitlGate(wait_fn=...) or Flower Chat gate.
    # F6: never skip HITL. AutoApprove is explicit dry-run only (hitl-auto-approve-dry-run=true).
    # When false, fail closed until Franco wires the real pause — do not silently Approve.
    if auto_hitl:
        hitl_gate = build_hitl_gate(mode="auto")
    else:
        _ = ConsoleHitlGate  # retained for local agent debugging
        raise RuntimeError(
            "HITL gate not wired (hitl-auto-approve-dry-run=false). "
            "F6 forbids silent auto-approve on the live path. "
            "TODO FRANCO: wire CallbackHitlGate(wait_fn=...). "
            "For fixture dry-runs set hitl-auto-approve-dry-run=true or use scripts/dry_run.py."
        )

    result = kickoff_credentialing(
        provider_id=provider_id,
        network_id=network_id,
        run_id=run_id,
        emitter=emitter,
        hitl_gate=hitl_gate,
        hospital=hospital,
        payer=payer,
        fixture_mode=fixture_mode,
    )

    # Persist outcome for run series
    state = getattr(context, "state", None)
    if state is not None and hasattr(state, "__setitem__"):
        try:
            state["privcred_outcome"] = result.outcome.value
            state["privcred_run_id"] = result.run_id
            if result.receipt:
                state["privcred_receipt_id"] = result.receipt.receipt_id
        except Exception:
            pass
