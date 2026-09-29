#!/usr/bin/env python3
"""F7 HITL claim review panel demo (FLOWER-3).

Judge-visible path:
  python scripts/run_f7_hitl.py --serve
  # open http://127.0.0.1:8765/ → Approve / Escalate / Reject
  # Approve → F8 receipt; Escalate/Reject → no receipt

CLI panel (no browser):
  python scripts/run_f7_hitl.py --cli

Scripted self-test (CI — still goes through PanelHitlGate, never AutoApprove):
  python scripts/run_f7_hitl.py --action approve
  python scripts/run_f7_hitl.py --action escalate
  python scripts/run_f7_hitl.py --action reject

Synthetic fixtures only. Auto-approve disabled on this path.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from poppy_orchestrator.clients.hospital_cred import StubHospitalCredClient
from poppy_orchestrator.clients.payer_enrollment import StubPayerEnrollmentClient
from poppy_orchestrator.contracts.claims import HitlAction
from poppy_orchestrator.events.emit import LocalEventBus
from poppy_orchestrator.hitl.panel_gate import (
    PanelHitlGate,
    console_panel_wait_fn,
    make_http_panel_gate,
)
from poppy_orchestrator.orchestration.flow import OrchestratorConfig, run_credentialing_flow


def _preset_panel_gate(action: str) -> PanelHitlGate:
    """Scripted gate that still uses PanelHitlGate (not AutoApproveHitlGate)."""

    def wait_fn(panel: dict, timeout_s: Optional[float]):
        _ = timeout_s
        assert panel.get("auto_approve") is False
        assert "approve" in panel.get("actions", [])
        return {
            "action": action,
            "actor": "f7-scripted-panel",
            "reason": f"scripted:{action}",
        }

    return PanelHitlGate(wait_fn=wait_fn, actor="f7-scripted-panel")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="F7 HITL claim review panel")
    parser.add_argument("--provider", default="SYNTH-NPI-1999999999")
    parser.add_argument("--network", default="SYNTH-NETWORK-X")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--serve",
        action="store_true",
        help="Local HTTP panel (default port 8765); blocks until human acts",
    )
    mode.add_argument(
        "--cli",
        action="store_true",
        help="Interactive CLI panel (re-prompt; never auto-approve)",
    )
    mode.add_argument(
        "--action",
        choices=["approve", "escalate", "reject"],
        help="Scripted panel decision via PanelHitlGate (CI / dry demo)",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        help="Seconds to wait for human decision when --serve (default 300)",
    )
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args(argv)

    if not args.serve and not args.cli and not args.action:
        args.action = "approve"  # CI-friendly default still uses PanelHitlGate

    server = None
    if args.serve:
        gate, server, _queue = make_http_panel_gate(
            host=args.host, port=args.port, timeout_s=args.timeout
        )
        url = server.start()
        print(f"Serving HITL panel at {url}")
    elif args.cli:
        gate = PanelHitlGate(wait_fn=console_panel_wait_fn(), actor="console-panel")
    else:
        gate = _preset_panel_gate(args.action)

    bus = LocalEventBus()
    try:
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
    finally:
        if server is not None:
            server.stop()

    if result.hitl is None:
        print("F7 violation: HITL decision missing — panel pause skipped", file=sys.stderr)
        return 1
    if not any(e.get("event") == "privcred.hitl.request" for e in bus.events):
        print("F7 violation: privcred.hitl.request never emitted", file=sys.stderr)
        return 1

    # Enforce: AutoApproveHitlGate must not be used on this script path
    if result.hitl.actor == "dry-run-auto":
        print("F7 violation: AutoApproveHitlGate used on panel path", file=sys.stderr)
        return 1

    summary = result.to_summary()
    summary["panel"] = {
        "mode": "serve" if args.serve else ("cli" if args.cli else f"action:{args.action}"),
        "auto_approve": False,
        "operator_elapsed_s": getattr(gate, "wait_elapsed_s", None),
        "operator_budget_s": 60,
    }
    if result.hitl.action == HitlAction.APPROVE:
        assert result.receipt is not None, "Approve must emit F8 receipt"
    else:
        assert result.receipt is None, "Escalate/Reject must not emit receipt"

    print("\n=== F7 HITL PANEL SUMMARY ===")
    print(json.dumps(summary, indent=2))
    if args.json_out:
        args.json_out.write_text(json.dumps(summary, indent=2))
        print(f"Wrote {args.json_out}")
    return 0


if __name__ == "__main__":
    from poppy_orchestrator.console import use_utf8_output

    use_utf8_output()
    raise SystemExit(main())
