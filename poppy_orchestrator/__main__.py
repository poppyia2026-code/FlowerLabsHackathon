"""CLI entry: python -m poppy_orchestrator

F5 kickoff — credential synthetic provider P for network X, fetch both
SuperNode claim slices, pause for HITL, emit claim receipt.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from poppy_orchestrator.agent_app import build_hitl_gate, kickoff_credentialing
from poppy_orchestrator.contracts.claims import HitlAction
from poppy_orchestrator.events.emit import LocalEventBus
from poppy_orchestrator.hitl.pause import CallbackHitlGate


def _preset_gate(action: str) -> CallbackHitlGate:
    mapped = {
        "approve": HitlAction.APPROVE,
        "escalate": HitlAction.ESCALATE,
        "reject": HitlAction.REJECT,
    }[action]

    def wait_fn(bundle: dict, timeout_s: Optional[float]):
        return {
            "action": mapped.value,
            "actor": "cli-preset",
            "reason": f"preset HITL action={mapped.value}",
        }

    return CallbackHitlGate(wait_fn=wait_fn)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m poppy_orchestrator",
        description=(
            "PrivCred PoppyOrchestrator F5 kickoff — credential provider P "
            "for network X (synthetic fixtures only)."
        ),
    )
    parser.add_argument(
        "--provider",
        default="SYNTH-NPI-1999999999",
        help="Synthetic provider_id (default: Provider P happy path)",
    )
    parser.add_argument(
        "--network",
        default="SYNTH-NETWORK-X",
        help="Synthetic network id (default: SYNTH-NETWORK-X)",
    )
    parser.add_argument(
        "--hitl",
        choices=["approve", "escalate", "reject", "console", "auto"],
        default="approve",
        help="HITL simulation mode (default: approve → receipt)",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Optional path to write FlowResult summary JSON",
    )
    args = parser.parse_args(argv)

    if args.hitl == "auto":
        gate = build_hitl_gate(mode="auto")
    elif args.hitl == "console":
        gate = build_hitl_gate(mode="console")
    else:
        gate = _preset_gate(args.hitl)

    bus = LocalEventBus()
    result = kickoff_credentialing(
        provider_id=args.provider,
        network_id=args.network,
        emitter=bus,
        hitl_gate=gate,
        fixture_mode=True,
    )

    if result.hitl is None:
        print("F5 violation: HITL decision missing — pause was skipped", file=sys.stderr)
        return 1
    hitl_reqs = [e for e in bus.events if e.get("event") == "privcred.hitl.request"]
    if not hitl_reqs:
        print("F5 violation: privcred.hitl.request never emitted", file=sys.stderr)
        return 1

    summary = result.to_summary()
    summary["events_count"] = len(bus.events)
    stage_events = [
        e.get("data", {}).get("stage")
        for e in bus.events
        if e.get("event") == "privcred.stage"
    ]
    summary["stages_emitted"] = stage_events

    print("\n=== F5 KICKOFF SUMMARY ===")
    print(json.dumps(summary, indent=2))
    if args.json_out:
        args.json_out.write_text(json.dumps(summary, indent=2))
        print(f"Wrote {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
