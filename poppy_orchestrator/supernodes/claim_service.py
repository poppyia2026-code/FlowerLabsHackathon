"""Shared SuperNode claim serving for F2 HospitalCred + F3 PayerEnrollment.

Fixture-backed only (F1 shards). Used by:
  - AgentApp stubs (hospital_cred_app / payer_enrollment_app)
  - FakeAgentGrid auto-replies
  - Grid-backed orchestrator claim fetch (local / tests)

No live CAQH / NPDB / PHI. No HITRUST / HIPAA-certified claims.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from poppy_orchestrator.clients.hospital_cred import StubHospitalCredClient
from poppy_orchestrator.clients.payer_enrollment import StubPayerEnrollmentClient
from poppy_orchestrator.contracts.claims import (
    HOSPITAL_CRED_CLAIMS,
    PAYER_ENROLLMENT_CLAIMS,
    ClaimRequest,
    ClaimResponse,
    ProviderRef,
    new_request_id,
)
from poppy_orchestrator.grid.roles import (
    ROLE_HOSPITAL_CRED,
    ROLE_PAYER_ENROLLMENT,
)

DEFAULT_PROVIDER = "SYNTH-NPI-1999999999"
DEFAULT_NETWORK = "SYNTH-NETWORK-X"


def _parse_inbound(payload: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    try:
        parsed = json.loads(payload)
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def claim_types_for_role(role: str) -> frozenset[str]:
    if role == ROLE_HOSPITAL_CRED:
        return HOSPITAL_CRED_CLAIMS
    if role == ROLE_PAYER_ENROLLMENT:
        return PAYER_ENROLLMENT_CLAIMS
    raise ValueError(f"unknown SuperNode role: {role}")


def build_claim_request(
    role: str,
    *,
    provider_id: str = DEFAULT_PROVIDER,
    network_id: str = DEFAULT_NETWORK,
    claim_types: Optional[tuple[str, ...]] = None,
) -> ClaimRequest:
    types = claim_types or tuple(sorted(claim_types_for_role(role)))
    prefix = "hosp" if role == ROLE_HOSPITAL_CRED else "pay"
    return ClaimRequest(
        request_id=new_request_id(prefix),
        provider=ProviderRef(provider_id=provider_id, network_id=network_id),
        claim_types=types,
        source_node=role,
    )


def serve_claims_for_role(
    role: str,
    *,
    provider_id: str = DEFAULT_PROVIDER,
    network_id: str = DEFAULT_NETWORK,
    claim_types: Optional[tuple[str, ...]] = None,
    hospital: Optional[StubHospitalCredClient] = None,
    payer: Optional[StubPayerEnrollmentClient] = None,
) -> ClaimResponse:
    """Serve typed F1 fixture claims for a SuperNode role (synthetic only)."""
    req = build_claim_request(
        role,
        provider_id=provider_id,
        network_id=network_id,
        claim_types=claim_types,
    )
    if role == ROLE_HOSPITAL_CRED:
        client = hospital or StubHospitalCredClient()
        return client.request_claims(req)
    if role == ROLE_PAYER_ENROLLMENT:
        client = payer or StubPayerEnrollmentClient()
        return client.request_claims(req)
    raise ValueError(f"unknown SuperNode role: {role}")


def handle_inbound_message(role: str, payload: str | dict[str, Any]) -> str:
    """Parse Orchestrator Grid payload → ClaimResponse JSON string.

    Accepts either a claim-request envelope from F0 handoff or a bare
    ``ClaimRequest``-shaped dict. Always marks synthetic.
    """
    data = _parse_inbound(payload)
    provider_id = str(
        data.get("provider_id")
        or (data.get("provider") or {}).get("provider_id")
        or DEFAULT_PROVIDER
    )
    network_id = str(
        data.get("network_id")
        or (data.get("provider") or {}).get("network_id")
        or DEFAULT_NETWORK
    )
    raw_types = data.get("claim_types")
    claim_types: Optional[tuple[str, ...]] = None
    if isinstance(raw_types, (list, tuple)) and raw_types:
        claim_types = tuple(str(t) for t in raw_types)

    try:
        resp = serve_claims_for_role(
            role,
            provider_id=provider_id,
            network_id=network_id,
            claim_types=claim_types,
        )
    except ValueError as exc:
        return json.dumps(
            {
                "ok": False,
                "error": str(exc),
                "source_node": role,
                "synthetic": True,
            },
            separators=(",", ":"),
        )
    out = resp.to_dict()
    out["synthetic"] = True
    out.setdefault("role", role)
    return json.dumps(out, separators=(",", ":"))


def roles_claim_slices() -> dict[str, list[str]]:
    """Document disjoint F2 / F3 slices for Leandro registration docs."""
    return {
        ROLE_HOSPITAL_CRED: sorted(HOSPITAL_CRED_CLAIMS),
        ROLE_PAYER_ENROLLMENT: sorted(PAYER_ENROLLMENT_CLAIMS),
    }
