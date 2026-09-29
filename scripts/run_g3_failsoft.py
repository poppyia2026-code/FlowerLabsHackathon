#!/usr/bin/env python3
"""G3 fail-soft offline path — FakeAgentGrid + HITL Approve + receipt (no SuperGrid)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from poppy_orchestrator.agent_app import kickoff_credentialing, run_f0_grid_handoff
from poppy_orchestrator.events.emit import LocalEventBus
from poppy_orchestrator.hitl.pause import AutoApproveHitlGate
from poppy_orchestrator.receipts.format import format_receipt_text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write fixtures/g3/offline_demo_summary.json",
    )
    parser.add_argument("--provider", default="SYNTH-NPI-1999999999")
    args = parser.parse_args()

    bus = LocalEventBus()
    handoff = run_f0_grid_handoff(
        provider_id=args.provider,
        network_id="SYNTH-NETWORK-X",
        emitter=bus,
    )
    # AutoApprove is dry-run only — documents offline kit path; live demo uses panel.
    result = kickoff_credentialing(
        provider_id=args.provider,
        hitl_gate=AutoApproveHitlGate(),
        emitter=bus,
    )

    summary = {
        "synthetic": True,
        "mode": "g3_failsoft_offline",
        "disclaimer": (
            "Offline demo path when SuperGrid flakes. Fixtures only — "
            "no live CAQH/NPDB/PHI. Not HITRUST / HIPAA-certified."
        ),
        "grid_handoff": handoff.to_summary(),
        "credentialing": result.to_summary(),
        "receipt_text": (
            format_receipt_text(result.receipt) if result.receipt else None
        ),
        "spoken_fallback_doc": "docs/g3-failsoft.md",
        "g1_runbook": "docs/g1-demo-runbook.md",
    }
    print(json.dumps(summary, indent=2))
    if result.receipt:
        print("\n--- receipt ---\n")
        print(format_receipt_text(result.receipt))

    if args.write:
        out = ROOT / "fixtures" / "g3" / "offline_demo_summary.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        # Stable-ish write: drop volatile ids unless present
        with out.open("w") as f:
            json.dump(summary, f, indent=2)
            f.write("\n")
        print(f"\nWrote {out}", file=sys.stderr)

    ok = handoff.ok and result.receipt is not None
    return 0 if ok else 1


if __name__ == "__main__":
    from poppy_orchestrator.console import use_utf8_output

    use_utf8_output()
    raise SystemExit(main())
