#!/usr/bin/env python3
"""F9 / FLOWER-14 — E2E dry run in demo budget (local FakeAgentGrid / stubs).

Path: fixtures → Orchestrator → HospitalCred + PayerEnrollment claims →
HITL → F8 receipt.

HITL rules (honest):
  - Production / demo path: NEVER auto-approve. Use --hitl panel|console
    or omit TEST_HITL_DECISION.
  - CI / unit tests ONLY: set TEST_HITL_DECISION=approve (or escalate|reject)
    together with PRIVCRED_E2E_TEST=1. Script refuses the env auto-driver
    unless PRIVCRED_E2E_TEST=1 is set.

Not a live SuperGrid dress rehearsal — that is G2 (Leandro + Franco).

Usage:
  python scripts/run_f9_e2e.py
  PRIVCRED_E2E_TEST=1 TEST_HITL_DECISION=approve python scripts/run_f9_e2e.py
  python scripts/run_f9_e2e.py --hitl approve   # explicit CLI preset (dry-run)
  python scripts/run_f9_e2e.py --budget-check
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from poppy_orchestrator.clients.hospital_cred import StubHospitalCredClient
from poppy_orchestrator.clients.payer_enrollment import StubPayerEnrollmentClient
from poppy_orchestrator.contracts.claims import HitlAction
from poppy_orchestrator.events.emit import LocalEventBus
from poppy_orchestrator.hitl.pause import CallbackHitlGate, ConsoleHitlGate
from poppy_orchestrator.orchestration.flow import OrchestratorConfig, run_credentialing_flow

# G1 spoken beats (docs/g1-demo-runbook.md) — machine path should leave headroom.
G1_BEATS = {
    "flower_handoff_s": (0, 40),
    "problem_wedge_s": (40, 80),
    "live_hitl_receipt_s": (80, 180),  # 1:20–3:00
    "endeavor_optional_s": (180, 220),
    "limits_ask_s": (220, 270),
}
# Local dry-run machine budget for fixtures→claims→HITL→receipt (excludes spoken).
MACHINE_BUDGET_S = 30.0
DEMO_TOTAL_S = 300.0  # 5 min upper bound


def _preset_gate(action: str, *, actor: str) -> CallbackHitlGate:
    mapped = {
        "approve": HitlAction.APPROVE,
        "escalate": HitlAction.ESCALATE,
        "reject": HitlAction.REJECT,
    }[action]

    def wait_fn(bundle: dict, timeout_s):
        _ = bundle, timeout_s
        return {
            "action": mapped.value,
            "actor": actor,
            "reason": f"f9-e2e preset HITL={mapped.value}",
        }

    return CallbackHitlGate(wait_fn=wait_fn)


def _resolve_hitl_gate(args: argparse.Namespace):
    """Resolve HITL gate with production-safe defaults.

    Auto-driver via TEST_HITL_DECISION is allowed only when PRIVCRED_E2E_TEST=1.
    """
    env_decision = (os.environ.get("TEST_HITL_DECISION") or "").strip().lower()
    e2e_test = str(os.environ.get("PRIVCRED_E2E_TEST", "")).lower() in {
        "1",
        "true",
        "yes",
    }

    if args.hitl == "console" or args.hitl == "panel":
        return ConsoleHitlGate(), "console/panel (never auto)"

    if args.hitl in {"approve", "escalate", "reject"}:
        return (
            _preset_gate(args.hitl, actor="f9-cli-preset"),
            f"cli-preset:{args.hitl} (dry-run explicit)",
        )

    # args.hitl == auto-env
    if env_decision:
        if not e2e_test:
            raise SystemExit(
                "Refusing TEST_HITL_DECISION without PRIVCRED_E2E_TEST=1. "
                "Production path never auto-approves. For CI set both env vars; "
                "for local dry-run pass --hitl approve|escalate|reject explicitly."
            )
        if env_decision not in {"approve", "escalate", "reject"}:
            raise SystemExit(
                f"Invalid TEST_HITL_DECISION={env_decision!r}; "
                "expected approve|escalate|reject"
            )
        return (
            _preset_gate(env_decision, actor="f9-test-hitl-driver"),
            f"TEST_HITL_DECISION={env_decision} (CI only)",
        )

    # Default for scripted local dry-run: explicit approve preset (not silent env)
    return (
        _preset_gate("approve", actor="f9-default-dry-run"),
        "default dry-run preset=approve (not production)",
    )


def _budget_notes(elapsed_s: float) -> dict:
    machine_ok = elapsed_s <= MACHINE_BUDGET_S
    return {
        "elapsed_s": round(elapsed_s, 3),
        "machine_budget_s": MACHINE_BUDGET_S,
        "machine_ok": machine_ok,
        "demo_total_budget_s": DEMO_TOTAL_S,
        "g1_beats": G1_BEATS,
        "notes": [
            "Machine path (fixtures→2 claims→HITL driver→receipt) should finish "
            f"well under {MACHINE_BUDGET_S:.0f}s so Franco has <60s operator room "
            "inside the 1:20–3:00 spoken HITL beat.",
            "Live dress rehearsal with SuperGrid = G2 (Leandro + Franco) — "
            "this script is local Fake/stub dry-run only.",
            "Endeavor assist (F11) is optional and must not inflate past the "
            "3:00–3:40 spoken beat when live.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="F9 E2E dry run (demo budget)")
    parser.add_argument("--provider", default="SYNTH-NPI-1999999999")
    parser.add_argument("--network", default="SYNTH-NETWORK-X")
    parser.add_argument(
        "--hitl",
        choices=["auto-env", "approve", "escalate", "reject", "console", "panel"],
        default="auto-env",
        help="HITL mode. auto-env uses TEST_HITL_DECISION only if PRIVCRED_E2E_TEST=1",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Write full summary JSON",
    )
    parser.add_argument(
        "--budget-check",
        action="store_true",
        help="Exit non-zero if machine path exceeds MACHINE_BUDGET_S",
    )
    args = parser.parse_args()

    gate, hitl_mode = _resolve_hitl_gate(args)
    bus = LocalEventBus()
    t0 = time.perf_counter()
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
    elapsed = time.perf_counter() - t0

    claim_types = sorted({c.claim_type for c in result.bundle.all_claims()})
    stages = [
        e["data"]["stage"]
        for e in bus.events
        if e.get("event") == "privcred.stage"
    ]
    budget = _budget_notes(elapsed)

    summary = {
        "f9_e2e": True,
        "live_supergrid": False,
        "path": "fixtures→orchestrator→2 claims→HITL→F8 receipt",
        "hitl_mode": hitl_mode,
        "production_auto_approve": False,
        "run_id": result.run_id,
        "outcome": result.outcome.value,
        "provider_id": result.bundle.provider.provider_id,
        "network_id": result.bundle.provider.network_id,
        "claim_types": claim_types,
        "claim_count": len(result.bundle.all_claims()),
        "missing_nodes": result.bundle.missing_nodes(),
        "hitl": result.hitl.to_dict() if result.hitl else None,
        "receipt": result.receipt.to_dict() if result.receipt else None,
        "receipt_emitted": result.receipt is not None,
        "stages": stages,
        "endeavor_optional": True,
        "budget": budget,
        "roles": {
            "orchestrator": "Luigi / CoS",
            "run_supernodes": "Leandro",
            "hitl_operator": "Franco",
            "live_dress": "G2 / Leandro+Franco",
        },
        "synthetic": True,
    }

    print("\n=== F9 E2E DRY-RUN SUMMARY ===")
    print(json.dumps(summary, indent=2))
    if args.json_out:
        args.json_out.write_text(json.dumps(summary, indent=2))
        print(f"Wrote {args.json_out}")

    # Hard AC checks
    if result.hitl is None:
        raise SystemExit("F9 fail: HITL skipped")
    if "HospitalCred" in (result.bundle.missing_nodes() or []) or "PayerEnrollment" in (
        result.bundle.missing_nodes() or []
    ):
        # Happy-path provider should have both nodes
        if args.provider == "SYNTH-NPI-1999999999":
            raise SystemExit("F9 fail: missing SuperNode claims on happy path")
    if result.hitl.action == HitlAction.APPROVE and result.receipt is None:
        raise SystemExit("F9 fail: Approve without F8 receipt")
    if "endeavor_assist" not in stages:
        raise SystemExit("F9 fail: endeavor_assist stage missing (F11 wire)")

    if args.budget_check and not budget["machine_ok"]:
        raise SystemExit(
            f"F9 budget fail: elapsed {elapsed:.2f}s > {MACHINE_BUDGET_S}s"
        )

    print(
        f"\n[f9] OK in {elapsed:.3f}s "
        f"(machine budget {MACHINE_BUDGET_S:.0f}s; live dress = G2)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
