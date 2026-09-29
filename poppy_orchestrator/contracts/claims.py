"""Typed claim contract for PrivCred PoppyOrchestrator (F5/F6).

Synthetic-only. Nodes return boolean / enum claims — never raw dossiers.

Claim ownership (disjoint attribute slices):
  HospitalCred      → work_history_complete, board_status
  PayerEnrollment   → license_active, npi_enumerated, exclusion_clear, enrollment_status

A node never answers a claim it does not own. It may raise a ClaimDispute
against another node's claim; the Orchestrator then re-asks the owner once.

TODO LEANDRO: keep SuperNode handlers aligned with these types.
TODO FRANCO: HITL panel displays ClaimBundle fields.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Mapping, Optional, Sequence

from poppy_orchestrator.contracts.privacy import (
    PrivacySummary,
    privacy_summary_from_dict,
)
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

# F1 (FLOWER-11) core typed claims — required for happy + escalate fixtures.
F1_CORE_CLAIMS: frozenset[str] = frozenset(
    {
        ClaimType.LICENSE_ACTIVE.value,
        ClaimType.NPI_ENUMERATED.value,
        ClaimType.EXCLUSION_CLEAR.value,
        ClaimType.WORK_HISTORY_COMPLETE.value,
    }
)

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
class ClaimDispute:
    """One node's objection to a claim that another node owns."""

    claim_type: str
    observed: Any  # what the disputing node sees for that claim
    raised_by: str = ""
    period: str = ""
    reason: str = ""
    evidence_ref: Optional[str] = None
    worded_by: Optional[str] = None  # model that worded `reason`, if any

    def __post_init__(self) -> None:
        if self.claim_type not in CLAIM_TYPES:
            raise ValueError(f"Unknown claim_type: {self.claim_type}")

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        if self.worded_by is None:
            del out["worded_by"]
        return out


@dataclass(frozen=True)
class ClaimRequest:
    """Orchestrator → SuperNode claim request."""

    request_id: str
    provider: ProviderRef
    claim_types: tuple[str, ...]
    source_node: str  # "HospitalCred" | "PayerEnrollment"
    requested_at: float = field(default_factory=lambda: time.time())
    synthetic: bool = True
    recheck: Optional[ClaimDispute] = None  # set on the follow-up round only

    def __post_init__(self) -> None:
        unknown = [c for c in self.claim_types if c not in CLAIM_TYPES]
        if unknown:
            raise ValueError(f"Unknown claim types: {unknown}")
        if not self.synthetic:
            raise ValueError("MVP allows synthetic=True only (no live CAQH/NPDB)")

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "request_id": self.request_id,
            "provider": self.provider.to_dict(),
            "claim_types": list(self.claim_types),
            "source_node": self.source_node,
            "requested_at": self.requested_at,
            "synthetic": self.synthetic,
        }
        if self.recheck is not None:
            out["recheck"] = self.recheck.to_dict()
        return out


@dataclass(frozen=True)
class ClaimDecision:
    """Single typed claim returned by a SuperNode."""

    claim_type: str
    value: Any  # bool | str enum
    confidence: float = 1.0
    evidence_ref: Optional[str] = None  # local fixture key — never raw file bytes
    notes: str = ""
    # Follow-up answers only: do the owner's records account for the dispute?
    resolves_dispute: Optional[bool] = None
    worded_by: Optional[str] = None  # model that worded `notes`, if any

    def __post_init__(self) -> None:
        if self.claim_type not in CLAIM_TYPES:
            raise ValueError(f"Unknown claim_type: {self.claim_type}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be in [0, 1]")

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        for optional in ("resolves_dispute", "worded_by"):
            if out[optional] is None:
                del out[optional]
        return out


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
    disputes: tuple[ClaimDispute, ...] = ()
    privacy_summary: Optional[PrivacySummary] = None

    def __post_init__(self) -> None:
        if not self.synthetic:
            raise ValueError("MVP allows synthetic=True only (no live CAQH/NPDB)")

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "request_id": self.request_id,
            "source_node": self.source_node,
            "provider_id": self.provider_id,
            "claims": [c.to_dict() for c in self.claims],
            "ok": self.ok,
            "error": self.error,
            "responded_at": self.responded_at,
            "synthetic": self.synthetic,
        }
        if self.disputes:
            out["disputes"] = [d.to_dict() for d in self.disputes]
        if self.privacy_summary is not None:
            out["privacy_summary"] = self.privacy_summary.to_dict()
        return out

    def get(self, claim_type: str) -> Optional[ClaimDecision]:
        for c in self.claims:
            if c.claim_type == claim_type:
                return c
        return None


CONFLICT_AGREED = "agreed"  # the owner now reports what the other node saw
CONFLICT_EXPLAINED = "explained"  # the owner's records account for the dispute
CONFLICT_UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class ClaimConflict:
    """Two nodes disagree on one claim; holds the owner's follow-up answer."""

    claim_type: str
    owner: str
    asserted: Any  # the owner's first answer
    dispute: ClaimDispute
    follow_up: Optional[ClaimDecision] = None

    @property
    def status(self) -> str:
        if self.follow_up is None:
            return CONFLICT_UNRESOLVED
        if self.follow_up.value == self.dispute.observed:
            return CONFLICT_AGREED
        if self.follow_up.resolves_dispute is True:
            return CONFLICT_EXPLAINED
        return CONFLICT_UNRESOLVED

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_type": self.claim_type,
            "owner": self.owner,
            "asserted": self.asserted,
            "dispute": self.dispute.to_dict(),
            "follow_up": self.follow_up.to_dict() if self.follow_up else None,
            "status": self.status,
        }


@dataclass
class ClaimBundle:
    """Aggregated claims for HITL panel + receipt."""

    run_id: str
    provider: ProviderRef
    hospital: Optional[ClaimResponse]
    payer: Optional[ClaimResponse]
    collected_at: float = field(default_factory=lambda: time.time())
    conflicts: tuple[ClaimConflict, ...] = ()

    def unresolved_conflicts(self) -> list[ClaimConflict]:
        return [c for c in self.conflicts if c.status == CONFLICT_UNRESOLVED]

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
        out: dict[str, Any] = {
            "run_id": self.run_id,
            "provider": self.provider.to_dict(),
            "hospital": self.hospital.to_dict() if self.hospital else None,
            "payer": self.payer.to_dict() if self.payer else None,
            "collected_at": self.collected_at,
            "missing_nodes": self.missing_nodes(),
            "claims": [c.to_dict() for c in self.all_claims()],
            "synthetic": True,
        }
        if self.conflicts:
            out["conflicts"] = [c.to_dict() for c in self.conflicts]
        return out


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


def claim_decision_from_dict(data: Mapping[str, Any]) -> ClaimDecision:
    return ClaimDecision(
        claim_type=data["claim_type"],
        value=data["value"],
        confidence=float(data.get("confidence", 1.0)),
        evidence_ref=data.get("evidence_ref"),
        notes=data.get("notes", ""),
        resolves_dispute=data.get("resolves_dispute"),
        worded_by=data.get("worded_by"),
    )


def claim_dispute_from_dict(
    data: Mapping[str, Any], *, raised_by: str = ""
) -> ClaimDispute:
    return ClaimDispute(
        claim_type=data["claim_type"],
        observed=data["observed"],
        raised_by=str(data.get("raised_by") or raised_by),
        period=str(data.get("period", "")),
        reason=str(data.get("reason", "")),
        evidence_ref=data.get("evidence_ref"),
        worded_by=data.get("worded_by"),
    )


def claim_conflict_from_dict(data: Mapping[str, Any]) -> ClaimConflict:
    follow_up = data.get("follow_up")
    return ClaimConflict(
        claim_type=data["claim_type"],
        owner=str(data["owner"]),
        asserted=data["asserted"],
        dispute=claim_dispute_from_dict(data["dispute"]),
        follow_up=claim_decision_from_dict(follow_up) if follow_up else None,
    )


def claim_response_from_dict(data: Mapping[str, Any]) -> ClaimResponse:
    claims = tuple(claim_decision_from_dict(c) for c in data.get("claims", []))
    if "synthetic" not in data:
        raise ValueError("claim response missing required field: synthetic")
    raw_privacy = data.get("privacy_summary")
    return ClaimResponse(
        request_id=str(data["request_id"]),
        source_node=str(data["source_node"]),
        provider_id=str(data["provider_id"]),
        claims=claims,
        ok=bool(data.get("ok", True)),
        error=data.get("error"),
        responded_at=float(data.get("responded_at", time.time())),
        synthetic=bool(data["synthetic"]),
        disputes=tuple(
            claim_dispute_from_dict(d, raised_by=str(data["source_node"]))
            for d in data.get("disputes", [])
        ),
        privacy_summary=(
            privacy_summary_from_dict(raw_privacy)
            if isinstance(raw_privacy, Mapping)
            else None
        ),
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
