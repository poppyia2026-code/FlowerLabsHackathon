"""Flower AgentApp entrypoint for PoppyOrchestrator.

AgentApp-only FAB (see pyproject.toml [tool.flwr.app.components]).
Do NOT add ServerApp/ClientApp to this bundle.

Live path requires SuperGrid credentials + Leandro SuperNodes + Franco HITL.
Local dry-run: `python scripts/dry_run.py` (no flwr / no API keys).
"""

from __future__ import annotations

from typing import Any

from poppy_orchestrator.clients.hospital_cred import StubHospitalCredClient
from poppy_orchestrator.clients.payer_enrollment import StubPayerEnrollmentClient
from poppy_orchestrator.events.emit import flower_emitter_from_session
from poppy_orchestrator.hitl.pause import AutoApproveHitlGate, ConsoleHitlGate
from poppy_orchestrator.orchestration.flow import OrchestratorConfig, run_credentialing_flow

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
            """flwr not installed — use scripts/dry_run.py locally."""

            def main(self):  # decorator no-op
                def deco(fn):
                    return fn

                return deco

        return _StubApp()
    return AgentApp()


app = _build_app()


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
    if fixture_mode:
        hospital = StubHospitalCredClient()
        payer = StubPayerEnrollmentClient()
    else:
        # Fail closed until Leandro wires real clients — do not invent credentials.
        raise RuntimeError(
            "fixture-mode=false but RealHospitalCredClient / RealPayerEnrollmentClient "
            "are not wired yet. TODO LEANDRO: implement and switch here."
        )

    # --- HITL gate ---
    # TODO FRANCO: replace with CallbackHitlGate(wait_fn=...) or Flower Chat gate.
    # F6: never skip HITL. AutoApprove is explicit dry-run only (hitl-auto-approve-dry-run=true).
    # When false, fail closed until Franco wires the real pause — do not silently Approve.
    if auto_hitl:
        hitl_gate = AutoApproveHitlGate()
    else:
        _ = ConsoleHitlGate  # retained for local agent debugging
        raise RuntimeError(
            "HITL gate not wired (hitl-auto-approve-dry-run=false). "
            "F6 forbids silent auto-approve on the live path. "
            "TODO FRANCO: wire CallbackHitlGate(wait_fn=...). "
            "For fixture dry-runs set hitl-auto-approve-dry-run=true or use scripts/dry_run.py."
        )

    config = OrchestratorConfig(
        provider_id=provider_id,
        network_id=network_id,
        run_id=run_id,
    )
    result = run_credentialing_flow(
        hospital=hospital,
        payer=payer,
        hitl_gate=hitl_gate,
        emitter=emitter,
        config=config,
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
