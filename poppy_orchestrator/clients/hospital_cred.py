"""HospitalCred SuperNode client.

Owns synthetic: education / work history / privileges / board flags.
Returns claims only: work_history_complete, board_status.

# TODO LEANDRO: replace StubHospitalCredClient body with real SuperNode /
# connector call on SuperGrid federation. Keep ClaimRequest/ClaimResponse
# contract stable (see schemas/claim_contract.schema.json).
# TODO LEANDRO: map SuperNode node-id / federation alias here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional, Protocol
import json
import time

from poppy_orchestrator.contracts.claims import (
    HOSPITAL_CRED_CLAIMS,
    ClaimDecision,
    ClaimRequest,
    ClaimResponse,
)
from poppy_orchestrator.clients.base import SuperNodeClaimClient

_REPO = Path(__file__).resolve().parents[2]
_FIXTURES = _REPO / "fixtures" / "supernodes" / "HospitalCred" / "providers.json"
_FIXTURES_FALLBACK = _REPO / "fixtures" / "providers.json"


class HospitalCredClient(Protocol):
    def request_claims(self, request: ClaimRequest) -> ClaimResponse: ...


class StubHospitalCredClient(SuperNodeClaimClient):
    """Fixture-backed stub for dry-run / unit tests.

    # TODO LEANDRO: RealHospitalCredClient(SuperNodeClaimClient) that:
    #   1. Serializes ClaimRequest.to_dict()
    #   2. Invokes SuperNode HospitalCred via agent.connectors / grid
    #   3. Parses ClaimResponse via claim_response_from_dict
    #   4. Never egresses raw dossier bytes
    """

    node_name = "HospitalCred"

    def __init__(self, fixtures_path: Optional[Path] = None) -> None:
        self._fixtures_path = fixtures_path or (_FIXTURES if _FIXTURES.is_file() else _FIXTURES_FALLBACK)
        self._providers = self._load()

    def _load(self) -> dict[str, Any]:
        with self._fixtures_path.open(encoding="utf-8") as f:
            data = json.load(f)
        return {p["provider_id"]: p for p in data["providers"]}

    def request_claims(self, request: ClaimRequest) -> ClaimResponse:
        bad = [t for t in request.claim_types if t not in HOSPITAL_CRED_CLAIMS]
        if bad:
            return ClaimResponse(
                request_id=request.request_id,
                source_node=self.node_name,
                provider_id=request.provider.provider_id,
                claims=(),
                ok=False,
                error=f"HospitalCred refuses claim types: {bad}",
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

        hospital: Mapping[str, Any] = provider.get("hospital_cred", {})
        if request.recheck is not None:
            return self._recheck(request, hospital, provider.get("rechecks", {}))

        decisions: list[ClaimDecision] = []
        for claim_type in request.claim_types:
            if claim_type not in hospital:
                return ClaimResponse(
                    request_id=request.request_id,
                    source_node=self.node_name,
                    provider_id=request.provider.provider_id,
                    claims=(),
                    ok=False,
                    error=f"fixture missing claim {claim_type}",
                )
            entry = hospital[claim_type]
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


    def _recheck(
        self,
        request: ClaimRequest,
        hospital: Mapping[str, Any],
        rechecks: Mapping[str, Any],
    ) -> ClaimResponse:
        """Look again at one claim another node disputed.

        Without a record for the disputed period the first answer stands and
        is marked as not accounting for the dispute.
        """
        dispute = request.recheck
        assert dispute is not None
        claim_type = dispute.claim_type
        first = hospital.get(claim_type)
        if first is None:
            return ClaimResponse(
                request_id=request.request_id,
                source_node=self.node_name,
                provider_id=request.provider.provider_id,
                claims=(),
                ok=False,
                error=f"fixture missing claim {claim_type}",
            )
        entry = rechecks.get(claim_type)
        if entry is None:
            decision = ClaimDecision(
                claim_type=claim_type,
                value=first["value"],
                confidence=float(first.get("confidence", 1.0)),
                evidence_ref=first.get("evidence_ref"),
                notes=f"No additional record for {dispute.period or 'the disputed period'}",
                resolves_dispute=False,
            )
        else:
            decision = ClaimDecision(
                claim_type=claim_type,
                value=entry["value"],
                confidence=float(entry.get("confidence", 1.0)),
                evidence_ref=entry.get("evidence_ref"),
                notes=entry.get("notes", ""),
                resolves_dispute=bool(entry.get("resolves_dispute", False)),
            )
        return ClaimResponse(
            request_id=request.request_id,
            source_node=self.node_name,
            provider_id=request.provider.provider_id,
            claims=(decision,),
            ok=True,
            responded_at=time.time(),
            synthetic=True,
        )


# TODO LEANDRO: class RealHospitalCredClient(SuperNodeClaimClient):
#     """Wire to SuperGrid SuperNode HospitalCred."""
#     node_name = "HospitalCred"
#     def __init__(self, agent_session, node_ref: str): ...
#     def request_claims(self, request: ClaimRequest) -> ClaimResponse: ...
