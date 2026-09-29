"""Named SuperNode / agent roles for judge-visible Grid handoffs (F0)."""

from __future__ import annotations

ROLE_ORCHESTRATOR = "PoppyOrchestrator"
ROLE_HOSPITAL_CRED = "HospitalCred"
ROLE_PAYER_ENROLLMENT = "PayerEnrollment"

# Expected federation roles for PrivCred MVP (≥2 for score playbook).
PRIVCRED_GRID_ROLES: tuple[str, ...] = (
    ROLE_HOSPITAL_CRED,
    ROLE_PAYER_ENROLLMENT,
)
