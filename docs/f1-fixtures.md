# F1 — Claim schema + synthetic fixtures (FLOWER-11)

Typed verification claims for PrivCred MVP. **Synthetic only** — no live
CAQH / NPDB / PHI. Do not claim HITRUST, HIPAA-certified sources, or speed %.

## F1 core claim types

| Claim | Owning SuperNode | Shape |
|-------|------------------|-------|
| `work_history_complete` | **HospitalCred** | bool |
| `license_active` | **PayerEnrollment** | bool |
| `npi_enumerated` | **PayerEnrollment** | bool |
| `exclusion_clear` | **PayerEnrollment** | bool |

F6 may also carry `board_status` (HospitalCred) and `enrollment_status`
(PayerEnrollment). Those are additive; F1 acceptance is the four rows above.

## SuperNode fixture layout (agreed path for Leandro)

```
fixtures/
  providers.json                              # Orchestrator aggregate (both slices)
  supernodes/
    HospitalCred/providers.json               # HospitalCred SuperNode shard
    PayerEnrollment/providers.json            # PayerEnrollment SuperNode shard
schemas/
  f1_claims.schema.json                       # F1 fixture + claim-type schema
  claim_contract.schema.json                  # F6 request/response/receipt contract
```

**Leandro wiring:** each SuperNode should load **only its shard** under
`fixtures/supernodes/<NodeName>/providers.json`. Orchestrator dry-run stubs
already prefer those paths (fallback: aggregate `fixtures/providers.json`).

Loader helpers: `poppy_orchestrator.fixtures.loader`
(`load_hospital_cred_catalog`, `load_payer_enrollment_catalog`,
`load_orchestrator_catalog`).

## Provider P fixtures

| Path | `provider_id` | Intent |
|------|---------------|--------|
| **happy** | `SYNTH-NPI-1999999999` | Provider P — all F1 claims clear → Approve → receipt |
| **escalate** | `SYNTH-NPI-1888888888` | Provider Q — work-history gap + exclusion flag → HITL Escalate |

Happy path F1 values (Provider P):

- `work_history_complete=true`
- `license_active=true`
- `npi_enumerated=true`
- `exclusion_clear=true`

Escalate path F1 values (Provider Q):

- `work_history_complete=false` (HospitalCred)
- `exclusion_clear=false` (PayerEnrollment)
- license / NPI still true (human reviews conflicting claims)

## Validate locally

```bash
# Schema + fixture tests (pytest + jsonschema)
python -m pytest tests/test_f1_claim_fixtures.py -v

# Stub clients still serve F5/F6 dry-run from SuperNode shards
python -m poppy_orchestrator --hitl approve
python -m poppy_orchestrator --provider SYNTH-NPI-1888888888 --hitl escalate
```

## Out of scope

- Live CAQH / NPDB / directory pulls
- Production PSV
- Claiming HIPAA-certified or HITRUST data sources
