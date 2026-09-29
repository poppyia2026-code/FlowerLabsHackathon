"""Flower AgentApp entrypoint for PoppyOrchestrator (F0 Grid tools + F5 kickoff).

AgentApp-only FAB (see pyproject.toml [tool.flwr.app.components]).
Do NOT add ServerApp/ClientApp to this bundle.

F0: agent.grid get_nodes → push_messages → pull_messages between
    Orchestrator ↔ HospitalCred / PayerEnrollment (judge-visible).
F5: kickoff credential P for network X → HITL → receipt.

Live path requires SuperGrid credentials + Leandro SuperNodes + Franco HITL.
Local dry-run / CLI:
  python -m poppy_orchestrator
  python scripts/run_f0_grid.py
  python scripts/run_f5.py
  python scripts/dry_run.py
  python scripts/run_f7_hitl.py --serve
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
from poppy_orchestrator.grid.fake_grid import FakeAgentGrid
from poppy_orchestrator.grid.handoff import GridHandoffResult, run_grid_role_handoff

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

    Modes:
      panel | console | cli — F7 claim review panel (never auto-approve)
      auto | approve — dry-run AutoApprove ONLY (still emits privcred.hitl.request)

    Live / judge demos: use panel/console or CallbackHitlGate — never silent skip.
    """
    normalized = (mode or "auto").lower()
    if normalized in {"console", "cli", "panel"}:
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



def run_f0_grid_handoff(
    *,
    grid: Any = None,
    provider_id: str = "SYNTH-NPI-1999999999",
    network_id: str = "SYNTH-NETWORK-X",
    emitter: Optional[EventEmitter] = None,
    sample_size: Optional[int] = None,
    pull_timeout: float = 0.0,
) -> GridHandoffResult:
    """F0: Collaborative AgentApp Grid tools handoff (≥2 roles).

    Uses live ``agent.grid`` when provided; otherwise FakeAgentGrid synthetic
    HospitalCred + PayerEnrollment nodes (local / unit tests).
    """
    if grid is None:
        grid = FakeAgentGrid()
    return run_grid_role_handoff(
        grid,
        provider_id=provider_id,
        network_id=network_id,
        sample_size=sample_size,
        pull_timeout=pull_timeout,
        emitter=emitter,
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

    # --- F0 Collaborative AgentApp Grid tools (≥2 roles) ---
    # Prefer live agent.grid on SuperGrid; fall back to FakeAgentGrid in fixtures.
    grid_enabled = str(run_config.get("grid-handoff", "true")).lower() in {
        "1",
        "true",
        "yes",
    }
    grid_handoff: Optional[GridHandoffResult] = None
    if grid_enabled:
        live_grid = getattr(agent, "grid", None)
        grid_handoff = run_f0_grid_handoff(
            grid=live_grid,
            provider_id=provider_id,
            network_id=network_id,
            emitter=emitter,
            sample_size=2,
            pull_timeout=float(run_config.get("grid-pull-timeout", 30) or 30),
        )
        if not grid_handoff.ok and live_grid is not None:
            # Live Grid without expected roles — fail closed for score path.
            raise RuntimeError(
                f"F0 Grid handoff failed: {grid_handoff.error}. "
                "Ensure HospitalCred + PayerEnrollment SuperNodes are in the federation."
            )

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
            if grid_handoff is not None:
                state["privcred_grid_handoff"] = grid_handoff.to_summary()
        except Exception:
            pass
