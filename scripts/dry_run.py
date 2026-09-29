#!/usr/bin/env python3
"""Local dry-run of PoppyOrchestrator — no SuperGrid credentials, no flwr required.

Usage:
  python scripts/dry_run.py
  python scripts/dry_run.py --provider SYNTH-NPI-1888888888 --hitl escalate
  python scripts/dry_run.py --hitl console   # interactive Approve/Escalate/Reject

Synthetic fixtures only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from poppy_orchestrator.clients.hospital_cred import StubHospitalCredClient
from poppy_orchestrator.clients.payer_enrollment import StubPayerEnrollmentClient
from poppy_orchestrator.contracts.claims import HitlAction
from poppy_orchestrator.events.emit import LocalEventBus
from poppy_orchestrator.hitl.pause import AutoApproveHitlGate, CallbackHitlGate, ConsoleHitlGate
from poppy_orchestrator.orchestration.flow import OrchestratorConfig, run_credentialing_flow


def _preset_gate(action: str) -> CallbackHitlGate:
    mapped = {
        "approve": HitlAction.APPROVE,
        "escalate": HitlAction.ESCALATE,
        "reject": HitlAction.REJECT,
    }[action]

    def wait_fn(bundle: dict, timeout_s):
        return {
            "action": mapped.value,
            "actor": "dry-run-preset",
            "reason": f"preset HITL action={mapped.value}",
        }

    return CallbackHitlGate(wait_fn=wait_fn)


def main() -> int:
    parser = argparse.ArgumentParser(description="PrivCred PoppyOrchestrator dry-run")
    parser.add_argument(
        "--provider",
        default="SYNTH-NPI-1999999999",
        help="Synthetic provider_id from fixtures/providers.json",
    )
    parser.add_argument("--network", default="SYNTH-NETWORK-X")
    parser.add_argument(
        "--hitl",
        choices=["approve", "escalate", "reject", "console", "auto"],
        default="approve",
        help="HITL simulation mode",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Optional path to write FlowResult summary JSON",
    )
    args = parser.parse_args()

    if args.hitl == "auto":
        gate = AutoApproveHitlGate()
    elif args.hitl == "console":
        gate = ConsoleHitlGate()
    else:
        gate = _preset_gate(args.hitl)

    bus = LocalEventBus()
    result = run_credentialing_flow(
        hospital=StubHospitalCredClient(),
        payer=StubPayerEnrollmentClient(),
        hitl_gate=gate,
        emitter=bus,
        config=OrchestratorConfig(
            provider_id=args.provider,
            network_id=args.network,
        ),
    )

    summary = {
        "run_id": result.run_id,
        "outcome": result.outcome.value,
        "provider_id": result.bundle.provider.provider_id,
        "missing_nodes": result.bundle.missing_nodes(),
        "claims": [c.to_dict() for c in result.bundle.all_claims()],
        "hitl": result.hitl.to_dict() if result.hitl else None,
        "receipt": result.receipt.to_dict() if result.receipt else None,
        "events_count": len(bus.events),
        "synthetic": True,
    }
    print("\n=== DRY-RUN SUMMARY ===")
    print(json.dumps(summary, indent=2))
    if args.json_out:
        args.json_out.write_text(json.dumps(summary, indent=2))
        print(f"Wrote {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
