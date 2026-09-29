#!/usr/bin/env python3
"""Local F2/F3 SuperNode stubs + FakeAgentGrid claim fetch (no SuperGrid)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from poppy_orchestrator.clients.grid_clients import (
    GridHospitalCredClient,
    GridPayerEnrollmentClient,
)
from poppy_orchestrator.contracts.claims import (
    HOSPITAL_CRED_CLAIMS,
    PAYER_ENROLLMENT_CLAIMS,
    ClaimRequest,
    ProviderRef,
    new_request_id,
)
from poppy_orchestrator.grid.fake_grid import FakeAgentGrid
from poppy_orchestrator.grid.handoff import run_grid_role_handoff
from poppy_orchestrator.supernodes.claim_service import (
    handle_inbound_message,
    roles_claim_slices,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--provider",
        default="SYNTH-NPI-1999999999",
        help="Synthetic provider id (F1 fixture)",
    )
    parser.add_argument("--network", default="SYNTH-NETWORK-X")
    parser.add_argument(
        "--role",
        choices=["HospitalCred", "PayerEnrollment", "both"],
        default="both",
    )
    args = parser.parse_args()

    print("=== F2/F3 claim slices (disjoint) ===")
    print(json.dumps(roles_claim_slices(), indent=2))

    payload = {
        "from": "PoppyOrchestrator",
        "to": args.role,
        "intent": "request_verification_claims",
        "provider_id": args.provider,
        "network_id": args.network,
        "synthetic": True,
    }

    if args.role in ("HospitalCred", "both"):
        print("\n=== HospitalCred stub reply ===")
        print(handle_inbound_message("HospitalCred", payload))
    if args.role in ("PayerEnrollment", "both"):
        print("\n=== PayerEnrollment stub reply ===")
        print(handle_inbound_message("PayerEnrollment", payload))

    if args.role != "both":
        return 0

    print("\n=== FakeAgentGrid handoff (F0) ===")
    grid = FakeAgentGrid()
    handoff = run_grid_role_handoff(
        grid,
        provider_id=args.provider,
        network_id=args.network,
        sample_size=2,
    )
    print(json.dumps(handoff.to_summary(), indent=2))

    print("\n=== Orchestrator Grid claim fetch ===")
    provider = ProviderRef(provider_id=args.provider, network_id=args.network)
    hosp = GridHospitalCredClient(grid=FakeAgentGrid()).request_claims(
        ClaimRequest(
            request_id=new_request_id("hosp"),
            provider=provider,
            claim_types=tuple(sorted(HOSPITAL_CRED_CLAIMS)),
            source_node="HospitalCred",
        )
    )
    pay = GridPayerEnrollmentClient(grid=FakeAgentGrid()).request_claims(
        ClaimRequest(
            request_id=new_request_id("pay"),
            provider=provider,
            claim_types=tuple(sorted(PAYER_ENROLLMENT_CLAIMS)),
            source_node="PayerEnrollment",
        )
    )
    print("HospitalCred ok=", hosp.ok, "claims=", len(hosp.claims))
    print("PayerEnrollment ok=", pay.ok, "claims=", len(pay.claims))
    print(json.dumps({"hospital": hosp.to_dict(), "payer": pay.to_dict()}, indent=2))
    return 0 if handoff.ok and hosp.ok and pay.ok else 1


if __name__ == "__main__":
    from poppy_orchestrator.console import use_utf8_output

    use_utf8_output()
    raise SystemExit(main())
