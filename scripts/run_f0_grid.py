#!/usr/bin/env python3
"""F0 dry-run: Collaborative AgentApp Grid tools between ≥2 roles.

Local synthetic path (no SuperGrid login required):

  python scripts/run_f0_grid.py

SuperGrid (once federation has HospitalCred + PayerEnrollment):

  flwr login supergrid
  flwr run . supergrid --stream
  # or: flwr chat   then select PrivCred PoppyOrchestrator

Judge-visible: Flower Chat activity / `flwr log <run-id> supergrid --show`
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running from repo root without install
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from poppy_orchestrator.agent_app import run_f0_grid_handoff  # noqa: E402
from poppy_orchestrator.events.emit import LocalEventBus  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="F0 Grid tools dry-run (synthetic)")
    parser.add_argument("--provider", default="SYNTH-NPI-1999999999")
    parser.add_argument("--network", default="SYNTH-NETWORK-X")
    parser.add_argument("--sample-size", type=int, default=2)
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args(argv)

    bus = LocalEventBus()
    result = run_f0_grid_handoff(
        provider_id=args.provider,
        network_id=args.network,
        sample_size=args.sample_size,
        emitter=bus,
    )
    summary = result.to_summary()
    summary["events_count"] = len(bus.events)
    summary["stages"] = [
        e.get("data", {}).get("stage")
        for e in bus.events
        if e.get("event") == "privcred.stage"
    ]
    print("\n=== F0 GRID HANDOFF SUMMARY ===")
    print(json.dumps(summary, indent=2))
    if args.json_out:
        args.json_out.write_text(json.dumps(summary, indent=2))
        print(f"Wrote {args.json_out}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    from poppy_orchestrator.console import use_utf8_output

    use_utf8_output()
    raise SystemExit(main())
