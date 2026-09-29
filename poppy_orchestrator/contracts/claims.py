"""Typed claim contract for PrivCred PoppyOrchestrator (F5/F6).

Synthetic-only. Nodes return boolean / enum claims — never raw dossiers.

Claim ownership (disjoint attribute slices):
  HospitalCred      → work_history_complete, board_status
  PayerEnrollment   → license_active, npi_enumerated, exclusion_clear, enrollment_status

TODO LEANDRO: keep SuperNode handlers aligned with these types.
TODO FRANCO: HITL panel displays ClaimBundle fields.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Mapping, Optional, Sequence
import time
import uuid


class ClaimType(str, Enum):
    LICENSE_ACTIVE = "license_active"
    BOARD_STATUS = "board_status"
    ENROLLMENT_STATUS = "enrollment_status"
    NPI_ENUMERATED = "npi_enumerated"
    EXCLUSION_CLEAR = "exclusion_clear"
    WORK_HISTORY_COMPLETE = "work_history_complete"


CLAIM_TYPES: tuple[str, ...] = tuple(c.value for c in ClaimType)

HOSPITAL_CRED_CLAIMS: frozenset[str] = frozenset(
    {ClaimType.WORK_HISTORY_COMPLETE.value, ClaimType.BOARD_STATUS.value}
)
PAYER_ENROLLMENT_CLAIMS: frozenset[str] = frozenset(
    {
        ClaimType.LICENSE_ACTIVE.value,
        ClaimType.NPI_ENUMERATED.value,
        ClaimType.EXCLUSION_CLEAR.value,
        ClaimType.ENROLLMENT_STATUS.value,
    }
)


class HitlAction(str, Enum):
    APPROVE = "approve"
    ESCALATE = "escalate"
    REJECT = "reject"


class CredentialingOutcome(str, Enum):
    CREDENTIALED = "credentialed"
    ESCALATED = "escalated"
    REJECTED = "rejected"
    FAILED = "failed"
    AWAITING_HITL = "awaiting_hitl"


@dataclass(frozen=True)
class ProviderRef:
    """Synthetic provider pointer — fake NPI-like id only."""

    provider_id: str
    network_id: str
    display_name: str = "Synthetic Provider P"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ClaimRequest:
    """Orchestrator → SuperNode claim request."""

    request_id: str
    provider: ProviderRef
    claim_types: tuple[str, ...]
    source_node: str  # "HospitalCred" | "PayerEnrollment"
    requested_at: float = field(default_factory=lambda: time.time())
    synthetic: bool = True

    def __post_init__(self) -> None:
        unknown = [c for c in self.claim_types if c not in CLAIM_TYPES]
        if unknown:
            raise ValueError(f"Unknown claim types: {unknown}")
        if not self.synthetic:
            raise ValueError("MVP allows synthetic=True only (no live CAQH/NPDB)")

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "provider": self.provider.to_dict(),
            "claim_types": list(self.claim_types),
            "source_node": self.source_node,
            "requested_at": self.requested_at,
            "synthetic": self.synthetic,
        }


@dataclass(frozen=True)
class ClaimDecision:
    """Single typed claim returned by a SuperNode."""

    claim_type: str
    value: Any  # bool | str enum
    confidence: float = 1.0
    evidence_ref: Optional[str] = None  # local fixture key — never raw file bytes
    notes: str = ""

    def __post_init__(self) -> None:
        if self.claim_type not in CLAIM_TYPES:
            raise ValueError(f"Unknown claim_type: {self.claim_type}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be in [0, 1]")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ClaimResponse:
    """SuperNode → Orchestrator claim response (claims only, no dossier)."""

    request_id: str
    source_node: str
    provider_id: str
    claims: tuple[ClaimDecision, ...]
    ok: bool = True
    error: Optional[str] = None
    responded_at: float = field(default_factory=lambda: time.time())
    synthetic: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "source_node": self.source_node,
            "provider_id": self.provider_id,
            "claims": [c.to_dict() for c in self.claims],
            "ok": self.ok,
            "error": self.error,
            "responded_at": self.responded_at,
            "synthetic": self.synthetic,
        }

    def get(self, claim_type: str) -> Optional[ClaimDecision]:
        for c in self.claims:
            if c.claim_type == claim_type:
                return c
        return None


@dataclass
class ClaimBundle:
    """Aggregated claims for HITL panel + receipt."""

    run_id: str
    provider: ProviderRef
    hospital: Optional[ClaimResponse]
    payer: Optional[ClaimResponse]
    collected_at: float = field(default_factory=lambda: time.time())

    def all_claims(self) -> list[ClaimDecision]:
        out: list[ClaimDecision] = []
        if self.hospital and self.hospital.ok:
            out.extend(self.hospital.claims)
        if self.payer and self.payer.ok:
            out.extend(self.payer.claims)
        return out

    def missing_nodes(self) -> list[str]:
        missing: list[str] = []
        if self.hospital is None or not self.hospital.ok:
            missing.append("HospitalCred")
        if self.payer is None or not self.payer.ok:
            missing.append("PayerEnrollment")
        return missing

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "provider": self.provider.to_dict(),
            "hospital": self.hospital.to_dict() if self.hospital else None,
            "payer": self.payer.to_dict() if self.payer else None,
            "collected_at": self.collected_at,
            "missing_nodes": self.missing_nodes(),
            "claims": [c.to_dict() for c in self.all_claims()],
            "synthetic": True,
        }


@dataclass(frozen=True)
class HitlDecision:
    action: HitlAction
    actor: str
    reason: str = ""
    decided_at: float = field(default_factory=lambda: time.time())

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action.value,
            "actor": self.actor,
            "reason": self.reason,
            "decided_at": self.decided_at,
        }


@dataclass(frozen=True)
class ClaimReceipt:
    """Auditable close after HITL (F8 hook)."""

    receipt_id: str
    run_id: str
    provider: ProviderRef
    outcome: CredentialingOutcome
    hitl: HitlDecision
    claims_snapshot: Sequence[Mapping[str, Any]]
    message: str
    issued_at: float = field(default_factory=lambda: time.time())
    synthetic: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "run_id": self.run_id,
            "provider": self.provider.to_dict(),
            "outcome": self.outcome.value,
            "hitl": self.hitl.to_dict(),
            "claims_snapshot": list(self.claims_snapshot),
            "message": self.message,
            "issued_at": self.issued_at,
            "synthetic": self.synthetic,
        }


def new_request_id(prefix: str = "req") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def new_receipt_id() -> str:
    return f"rcpt-{uuid.uuid4().hex[:12]}"


def claim_request_to_dict(req: ClaimRequest) -> dict[str, Any]:
    return req.to_dict()


def claim_response_from_dict(data: Mapping[str, Any]) -> ClaimResponse:
    claims = tuple(
        ClaimDecision(
            claim_type=c["claim_type"],
            value=c["value"],
            confidence=float(c.get("confidence", 1.0)),
            evidence_ref=c.get("evidence_ref"),
            notes=c.get("notes", ""),
        )
        for c in data.get("claims", [])
    )
    return ClaimResponse(
        request_id=str(data["request_id"]),
        source_node=str(data["source_node"]),
        provider_id=str(data["provider_id"]),
        claims=claims,
        ok=bool(data.get("ok", True)),
        error=data.get("error"),
        responded_at=float(data.get("responded_at", time.time())),
        synthetic=bool(data.get("synthetic", True)),
    )


def validate_claim_response(
    response: ClaimResponse,
    expected_types: Sequence[str],
    *,
    allowed_for_node: Optional[frozenset[str]] = None,
) -> list[str]:
    """Return list of validation errors (empty = ok). Never silently skip HITL."""
    errors: list[str] = []
    if not response.synthetic:
        errors.append("non-synthetic response rejected in MVP")
    if not response.ok:
        errors.append(response.error or "node returned ok=false")
        return errors
    got = {c.claim_type for c in response.claims}
    for t in expected_types:
        if t not in got:
            errors.append(f"missing claim: {t}")
    if allowed_for_node:
        for t in got:
            if t not in allowed_for_node:
                errors.append(f"claim {t} not allowed for node {response.source_node}")
    return errors
