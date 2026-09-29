#!/usr/bin/env python3
"""F8 helper: run Approve path and print screenshotable receipt (JSON + text)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from poppy_orchestrator.agent_app import kickoff_credentialing
from poppy_orchestrator.contracts.claims import HitlAction
from poppy_orchestrator.events.emit import LocalEventBus
from poppy_orchestrator.hitl.pause import CallbackHitlGate
from poppy_orchestrator.receipts.emit import enrich_receipt_dict
from poppy_orchestrator.receipts.format import (
    format_receipt_json,
    format_receipt_text,
    write_receipt_artifacts,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Print F8 auditable claim receipt (Approve path)")
    parser.add_argument("--provider", default="SYNTH-NPI-1999999999")
    parser.add_argument("--out-dir", type=Path, default=None, help="Optional dir for .json/.txt")
    args = parser.parse_args()

    def wait_fn(bundle, timeout_s):
        return {"action": HitlAction.APPROVE.value, "actor": "print-receipt", "reason": "F8 demo"}

    bus = LocalEventBus()
    result = kickoff_credentialing(
        provider_id=args.provider,
        emitter=bus,
        hitl_gate=CallbackHitlGate(wait_fn=wait_fn),
    )
    if result.receipt is None:
        print("No receipt — HITL did not Approve", file=sys.stderr)
        return 1
    payload = enrich_receipt_dict(result.receipt)
    print(format_receipt_text(payload))
    print("--- JSON ---")
    print(format_receipt_json(payload), end="")
    if args.out_dir:
        paths = write_receipt_artifacts(payload, args.out_dir, stem="receipt")
        print(f"Wrote {paths['json']} and {paths['txt']}")
    return 0


if __name__ == "__main__":
    from poppy_orchestrator.console import use_utf8_output

    use_utf8_output()
    raise SystemExit(main())
