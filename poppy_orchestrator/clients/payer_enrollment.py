"""PayerEnrollment SuperNode client.

Owns synthetic: NPI match, license flag, exclusion flag, enrollment status.
Returns claims only: license_active, npi_enumerated, exclusion_clear, enrollment_status.

# TODO LEANDRO: replace StubPayerEnrollmentClient with real SuperNode /
# connector call on SuperGrid federation. Keep ClaimRequest/ClaimResponse
# contract stable (see schemas/claim_contract.schema.json).
# TODO LEANDRO: ensure attribute slice stays disjoint from HospitalCred.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional, Protocol
import json
import time

from poppy_orchestrator.contracts.claims import (
    PAYER_ENROLLMENT_CLAIMS,
    ClaimDecision,
    ClaimRequest,
    ClaimResponse,
)
from poppy_orchestrator.clients.base import SuperNodeClaimClient

_REPO = Path(__file__).resolve().parents[2]
_FIXTURES = _REPO / "fixtures" / "supernodes" / "PayerEnrollment" / "providers.json"
_FIXTURES_FALLBACK = _REPO / "fixtures" / "providers.json"


class PayerEnrollmentClient(Protocol):
    def request_claims(self, request: ClaimRequest) -> ClaimResponse: ...


class StubPayerEnrollmentClient(SuperNodeClaimClient):
    """Fixture-backed stub for dry-run / unit tests.

    # TODO LEANDRO: RealPayerEnrollmentClient(SuperNodeClaimClient) that:
    #   1. Serializes ClaimRequest.to_dict()
    #   2. Invokes SuperNode PayerEnrollment via agent.connectors / grid
    #   3. Parses ClaimResponse via claim_response_from_dict
    #   4. Never egresses raw dossier bytes
    """

    node_name = "PayerEnrollment"

    def __init__(self, fixtures_path: Optional[Path] = None) -> None:
        self._fixtures_path = fixtures_path or (_FIXTURES if _FIXTURES.is_file() else _FIXTURES_FALLBACK)
        self._providers = self._load()

    def _load(self) -> dict[str, Any]:
        with self._fixtures_path.open() as f:
            data = json.load(f)
        return {p["provider_id"]: p for p in data["providers"]}

    def request_claims(self, request: ClaimRequest) -> ClaimResponse:
        bad = [t for t in request.claim_types if t not in PAYER_ENROLLMENT_CLAIMS]
        if bad:
            return ClaimResponse(
                request_id=request.request_id,
                source_node=self.node_name,
                provider_id=request.provider.provider_id,
                claims=(),
                ok=False,
                error=f"PayerEnrollment refuses claim types: {bad}",
            )

        provider = self._providers.get(request.provider.provider_id)
        if provider is None:
            return ClaimResponse(
                request_id=request.request_id,
                source_node=self.node_name,
                provider_id=request.provider.provider_id,
                claims=(),
                ok=False,
                error=f"unknown synthetic provider: {request.provider.provider_id}",
            )

        payer: Mapping[str, Any] = provider.get("payer_enrollment", {})
        decisions: list[ClaimDecision] = []
        for claim_type in request.claim_types:
            if claim_type not in payer:
                return ClaimResponse(
                    request_id=request.request_id,
                    source_node=self.node_name,
                    provider_id=request.provider.provider_id,
                    claims=(),
                    ok=False,
                    error=f"fixture missing claim {claim_type}",
                )
            entry = payer[claim_type]
            decisions.append(
                ClaimDecision(
                    claim_type=claim_type,
                    value=entry["value"],
                    confidence=float(entry.get("confidence", 1.0)),
                    evidence_ref=entry.get("evidence_ref"),
                    notes=entry.get("notes", ""),
                )
            )

        return ClaimResponse(
            request_id=request.request_id,
            source_node=self.node_name,
            provider_id=request.provider.provider_id,
            claims=tuple(decisions),
            ok=True,
            responded_at=time.time(),
            synthetic=True,
        )


# TODO LEANDRO: class RealPayerEnrollmentClient(SuperNodeClaimClient):
#     """Wire to SuperGrid SuperNode PayerEnrollment."""
#     node_name = "PayerEnrollment"
#     def __init__(self, agent_session, node_ref: str): ...
#     def request_claims(self, request: ClaimRequest) -> ClaimResponse: ...
