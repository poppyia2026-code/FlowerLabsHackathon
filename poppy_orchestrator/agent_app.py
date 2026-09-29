"""Flower AgentApp entrypoint for PoppyOrchestrator (F0 Grid tools + F5 kickoff).

AgentApp-only FAB (see pyproject.toml [tool.flwr.app.components]).
Do NOT add ServerApp/ClientApp to this bundle.

F0: agent.grid get_nodes → push_messages → pull_messages between
    Orchestrator ↔ HospitalCred / PayerEnrollment (judge-visible).
F5: kickoff credential P for network X → HITL → receipt.

Live path uses two configured SuperNodes and explicit review in Flower Chat.
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
from poppy_orchestrator.clients.grid_clients import (
    GridHospitalCredClient,
    GridPayerEnrollmentClient,
)
from poppy_orchestrator.events.emit import EventEmitter
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


def build_grid_clients(
    grid: Any = None,
) -> tuple[SuperNodeClaimClient, SuperNodeClaimClient]:
    """Claim clients that fetch via FakeAgentGrid / live agent.grid (F2/F3).

    Local tests: omit grid → FakeAgentGrid auto-replies with F1 fixtures.
    Live: pass agent.grid once Leandro registers HospitalCred + PayerEnrollment.
    """
    return (
        GridHospitalCredClient(grid=grid),
        GridPayerEnrollmentClient(grid=grid),
    )


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
    """Flower runtime: real Grid requests and explicit review in Flower Chat."""
    from poppy_orchestrator.live_runtime import run_live_agent

    run_live_agent(agent, context)
