"""F3 SuperNode PayerEnrollment AgentApp stub (FLOWER-12).

Serves F1 fixture claims: license_active, npi_enumerated, exclusion_clear,
enrollment_status. Slice is disjoint from HospitalCred (F2).

Federation name for Leandro: **PayerEnrollment**

Local (no SuperGrid):
  python -m poppy_orchestrator.supernodes.payer_enrollment_app
  python scripts/run_f2_f3_stubs.py --role PayerEnrollment

Live (Leandro — FLOWER-10):
  flwr login supergrid
  # Register this AgentApp as SuperNode named PayerEnrollment
  # See docs/f2-f3-supernodes.md
"""

from __future__ import annotations

import json
import sys
from typing import Any

from poppy_orchestrator.grid.roles import ROLE_PAYER_ENROLLMENT
from poppy_orchestrator.supernodes.claim_service import (
    handle_inbound_message,
    serve_claims_for_role,
)

try:
    from flwr.agentapp import AgentApp  # type: ignore
except ImportError:  # pragma: no cover
    try:
        from flwr.agent import AgentApp  # type: ignore
    except ImportError:  # pragma: no cover
        AgentApp = None  # type: ignore


def _build_app() -> Any:
    if AgentApp is None:

        class _StubApp:
            def main(self):
                def deco(fn):
                    return fn

                return deco

        return _StubApp()
    return AgentApp()


app = _build_app()

ROLE = ROLE_PAYER_ENROLLMENT


def serve_payload(payload: str | dict[str, Any]) -> str:
    """Handle Orchestrator claim-request → ClaimResponse JSON."""
    return handle_inbound_message(ROLE, payload)


@app.main()
def main(agent: Any, context: Any) -> None:
    """Serve this role from a configured local shard and reply via Flower."""
    from poppy_orchestrator.supernodes.runtime import serve_runtime_instruction

    serve_runtime_instruction(agent, context, ROLE)


def _cli() -> int:
    provider = "SYNTH-NPI-1999999999"
    network = "SYNTH-NETWORK-X"
    if len(sys.argv) > 1:
        provider = sys.argv[1]
    if len(sys.argv) > 2:
        network = sys.argv[2]
    payload = {
        "from": "PoppyOrchestrator",
        "to": ROLE,
        "intent": "request_verification_claims",
        "provider_id": provider,
        "network_id": network,
        "synthetic": True,
    }
    print(serve_payload(payload))
    return 0


if __name__ == "__main__":
    from poppy_orchestrator.console import use_utf8_output

    use_utf8_output()
    raise SystemExit(_cli())
