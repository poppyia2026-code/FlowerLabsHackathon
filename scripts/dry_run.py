#!/usr/bin/env python3
"""Local dry-run of PoppyOrchestrator — no SuperGrid credentials, no flwr required.

Prefer F5 CLI: ``python -m poppy_orchestrator`` or ``python scripts/run_f5.py``.

Usage:
  python scripts/dry_run.py
  python scripts/dry_run.py --provider SYNTH-NPI-1888888888 --hitl escalate
  python scripts/dry_run.py --hitl console   # interactive Approve/Escalate/Reject
  python scripts/dry_run.py --self-test      # F6 contract asserts (HITL + missing node)

Synthetic fixtures only.
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

from poppy_orchestrator.clients.base import SuperNodeClaimClient
from poppy_orchestrator.clients.hospital_cred import StubHospitalCredClient
from poppy_orchestrator.clients.payer_enrollment import StubPayerEnrollmentClient
from poppy_orchestrator.contracts.claims import (
    ClaimRequest,
    ClaimResponse,
    CredentialingOutcome,
    HitlAction,
)
from poppy_orchestrator.events.emit import LocalEventBus, NullEmitter
from poppy_orchestrator.hitl.pause import AutoApproveHitlGate, CallbackHitlGate, ConsoleHitlGate
from poppy_orchestrator.orchestration.flow import OrchestratorConfig, run_credentialing_flow

SCHEMA_PATH = ROOT / "schemas" / "claim_contract.schema.json"


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


class _MissingNodeClient(SuperNodeClaimClient):
    def __init__(self, node_name: str) -> None:
        self.node_name = node_name

    def request_claims(self, request: ClaimRequest) -> ClaimResponse:
        return ClaimResponse(
            request_id=request.request_id,
            source_node=self.node_name,
            provider_id=request.provider.provider_id,
            claims=(),
            ok=False,
            error=f"{self.node_name} unavailable (dry-run missing-node self-test)",
            synthetic=True,
        )


def _assert_hitl_pause(result, bus: LocalEventBus) -> None:
    """Fail closed if HITL was skipped (F6: never skip HITL)."""
    if result.hitl is None:
        raise SystemExit("F6 violation: HITL decision missing — pause was skipped")
    hitl_reqs = [e for e in bus.events if e.get("event") == "privcred.hitl.request"]
    if not hitl_reqs:
        raise SystemExit("F6 violation: privcred.hitl.request never emitted")


def _validate_schema_samples() -> None:
    """Validate stub claim request/response against schemas/claim_contract.schema.json."""
    try:
        import jsonschema
    except ImportError as exc:
        raise SystemExit(
            "jsonschema required for --self-test schema checks "
            "(pip install jsonschema). Re-run without --self-test for basic dry-run."
        ) from exc

    with SCHEMA_PATH.open(encoding="utf-8") as f:
        schema = json.load(f)

    def validate(instance: dict, definition: str) -> None:
        resolver_schema = {
            "$schema": schema.get("$schema"),
            "$ref": f"#/definitions/{definition}",
            "definitions": schema["definitions"],
        }
        jsonschema.validate(instance=instance, schema=resolver_schema)

    from poppy_orchestrator.contracts.claims import (
        HOSPITAL_CRED_CLAIMS,
        PAYER_ENROLLMENT_CLAIMS,
        ProviderRef,
        new_request_id,
    )

    provider = ProviderRef(provider_id="SYNTH-NPI-1999999999", network_id="SYNTH-NETWORK-X")
    hosp = StubHospitalCredClient()
    pay = StubPayerEnrollmentClient()
    hosp_req = ClaimRequest(
        request_id=new_request_id("hosp"),
        provider=provider,
        claim_types=tuple(sorted(HOSPITAL_CRED_CLAIMS)),
        source_node="HospitalCred",
    )
    pay_req = ClaimRequest(
        request_id=new_request_id("pay"),
        provider=provider,
        claim_types=tuple(sorted(PAYER_ENROLLMENT_CLAIMS)),
        source_node="PayerEnrollment",
    )
    validate(hosp_req.to_dict(), "claim_request")
    validate(pay_req.to_dict(), "claim_request")
    validate(hosp.request_claims(hosp_req).to_dict(), "claim_response")
    validate(pay.request_claims(pay_req).to_dict(), "claim_response")
    print("[self-test] claim request/response validate against claim_contract.schema.json")


def _run_missing_node_self_test() -> None:
    """Approve path with missing HospitalCred must fail closed (not credentialed)."""
    gate = _preset_gate("approve")
    result = run_credentialing_flow(
        hospital=_MissingNodeClient("HospitalCred"),
        payer=StubPayerEnrollmentClient(),
        hitl_gate=gate,
        emitter=NullEmitter(),
        config=OrchestratorConfig(provider_id="SYNTH-NPI-1999999999"),
    )
    if result.hitl is None:
        raise SystemExit("F6 violation: HITL skipped on missing-node path")
    if "HospitalCred" not in result.bundle.missing_nodes():
        raise SystemExit("F6 violation: missing HospitalCred not reported")
    if result.outcome != CredentialingOutcome.FAILED:
        raise SystemExit(
            f"F6 violation: expected FAILED on missing node, got {result.outcome.value}"
        )
    print("[self-test] missing node → HITL still runs → outcome=failed ✓")


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
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Also assert F6: HITL pause, missing-node fail, schema validation",
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

    _assert_hitl_pause(result, bus)

    summary = {
        "run_id": result.run_id,
        "outcome": result.outcome.value,
        "provider_id": result.bundle.provider.provider_id,
        "missing_nodes": result.bundle.missing_nodes(),
        "claims": [c.to_dict() for c in result.bundle.all_claims()],
        "hitl": result.hitl.to_dict() if result.hitl else None,
        "receipt": result.receipt.to_dict() if result.receipt else None,
        "events_count": len(bus.events),
        "hitl_pause_reached": True,
        "synthetic": True,
    }
    print("\n=== DRY-RUN SUMMARY ===")
    print(json.dumps(summary, indent=2))
    if args.json_out:
        args.json_out.write_text(json.dumps(summary, indent=2))
        print(f"Wrote {args.json_out}")

    if args.self_test:
        _run_missing_node_self_test()
        _validate_schema_samples()
        print("[self-test] F6 HITL + claim-contract checks passed")

    return 0


if __name__ == "__main__":
    from poppy_orchestrator.console import use_utf8_output

    use_utf8_output()
    raise SystemExit(main())
