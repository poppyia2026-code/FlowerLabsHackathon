# H4a — Payer-enrollment claim types beyond MVP (FLOWER-25)

**Parent:** FLOWER-22 · **not MVP**  
**Synthetic-first** path only until integrations are real.

## Goal

Expand beyond MVP typed flags (`license_active`, `npi_enumerated`, `exclusion_clear`, `work_history_complete`) with enrollment-oriented claim metaphors for payer network ops.

## Proposed claim types (metaphors)

| Claim type | Intent | Notes |
|------------|--------|-------|
| `network_participation` | Provider eligible for plan/network slice | Boolean + network_id; synthetic fixtures first |
| `specialty_assigned` | Specialty credential mapped for enrollment | Code + display; no live taxonomy sync in v1 |
| `location_assigned` | Practice location accepted for network | Site id; privacy: keep address on SuperNode |
| `panel_status` | Open / closed / limited panel | PayerEnrollment-owned attribute |

## Acceptance criteria (backlog)

- [ ] JSON Schema extensions documented alongside `schemas/`
- [ ] Synthetic fixtures for happy + escalate paths
- [ ] HITL still required before receipt
- [ ] No live CAQH enrollment API in this slice

## Out of scope

Implementing in Epic F today · live CAQH · HITRUST-as-ours
