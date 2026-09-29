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
from poppy_orchestrator.clients.hospital_cred import StubHospitalCredClient
from poppy_orchestrator.clients.payer_enrollment import StubPayerEnrollmentClient
from poppy_orchestrator.contracts.claims import (
    HOSPITAL_CRED_CLAIMS,
    PAYER_ENROLLMENT_CLAIMS,
    ClaimBundle,
    ClaimRequest,
    ProviderRef,
    new_request_id,
)
from poppy_orchestrator.events.emit import LocalEventBus
from poppy_orchestrator.hitl.pause import AutoApproveHitlGate
from poppy_orchestrator.hitl.stayed_traveled import (
    build_stayed_traveled_view,
    render_stayed_traveled_html,
)
from poppy_orchestrator.receipts.format import format_receipt_text



def _write_stayed_traveled(provider_id: str) -> None:
    """F13 screenshotable artifact for G3 fail-soft kit."""
    provider = ProviderRef(
        provider_id=provider_id,
        network_id="SYNTH-NETWORK-X",
        display_name="Synthetic Provider P (happy path)",
    )
    hospital = StubHospitalCredClient().request_claims(
        ClaimRequest(
            request_id=new_request_id("hosp"),
            provider=provider,
            claim_types=tuple(sorted(HOSPITAL_CRED_CLAIMS)),
            source_node="HospitalCred",
        )
    )
    payer = StubPayerEnrollmentClient().request_claims(
        ClaimRequest(
            request_id=new_request_id("pay"),
            provider=provider,
            claim_types=tuple(sorted(PAYER_ENROLLMENT_CLAIMS)),
            source_node="PayerEnrollment",
        )
    )
    bundle = ClaimBundle(
        run_id="g3-stayed-traveled",
        provider=provider,
        hospital=hospital,
        payer=payer,
    )
    view = build_stayed_traveled_view(bundle)
    out_dir = ROOT / "fixtures" / "g3"
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / "stayed_vs_traveled.html"
    json_path = out_dir / "stayed_vs_traveled.json"
    html_path.write_text(render_stayed_traveled_html(view))
    with json_path.open("w") as f:
        json.dump(view.to_dict(), f, indent=2)
        f.write("\n")
    print(f"Wrote {html_path}", file=sys.stderr)
    print(f"Wrote {json_path}", file=sys.stderr)


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
        _write_stayed_traveled(args.provider)

    ok = handoff.ok and result.receipt is not None
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
