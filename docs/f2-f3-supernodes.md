# F2 / F3 — SuperNode HospitalCred + PayerEnrollment scaffolds

**Runtime update:** use [F4 live runtime](f4-live-runtime.md) for deployment.
The same FAB now dispatches at each SuperNode using local `poppy-role` and
`poppy-data` configuration, reads Flower's instruction envelope, and returns
the requested provider's claims. The separate-FAB suggestion and coordinator
TODO below describe the original scaffold and are superseded by that guide.

**Status:** code scaffold complete (fixtures + AgentApp stubs + FakeAgentGrid
wire). **Live SuperGrid registration is Leandro / FLOWER-10** — do not claim
live federation until `flwr login` + register succeeds.

| Ticket | Role | Slice (disjoint) |
|--------|------|------------------|
| FLOWER-9 · F2 | **HospitalCred** | `work_history_complete`, `board_status` |
| FLOWER-12 · F3 | **PayerEnrollment** | `license_active`, `npi_enumerated`, `exclusion_clear`, `enrollment_status` |

Synthetic only. No live CAQH / NPDB / PHI. No HITRUST / HIPAA-certified claims.

## What CoS shipped (registerable stubs)

| Piece | Path |
|-------|------|
| Shared claim service | `poppy_orchestrator/supernodes/claim_service.py` |
| HospitalCred AgentApp stub | `poppy_orchestrator/supernodes/hospital_cred_app.py` → `app` |
| PayerEnrollment AgentApp stub | `poppy_orchestrator/supernodes/payer_enrollment_app.py` → `app` |
| Fixture shards | `fixtures/supernodes/{HospitalCred,PayerEnrollment}/providers.json` |
| FakeAgentGrid auto-reply | uses claim service (F0 handoff) |
| Orchestrator Grid fetch | `GridHospitalCredClient` / `GridPayerEnrollmentClient` |

## Local (no SuperGrid — fixtures only)

```bash
# Serve one role claim reply (happy path Provider P)
python -m poppy_orchestrator.supernodes.hospital_cred_app
python -m poppy_orchestrator.supernodes.payer_enrollment_app

# Both roles + FakeAgentGrid + orchestrator Grid claim fetch
python scripts/run_f2_f3_stubs.py
python scripts/run_f2_f3_stubs.py --provider SYNTH-NPI-1888888888

python -m pytest tests/test_f2_f3_supernode_stubs.py -v
```

## Leandro — live SuperGrid registration (FLOWER-10)

Federation must expose **exactly named** SuperNodes so Orchestrator Grid
`get_nodes` can match roles:

1. **HospitalCred** — point AgentApp at
   `poppy_orchestrator.supernodes.hospital_cred_app:app`
2. **PayerEnrollment** — point AgentApp at
   `poppy_orchestrator.supernodes.payer_enrollment_app:app`

Suggested sequence:

```bash
flwr login supergrid

# Bring up / register ≥2 SuperNodes with the names above (federation UI or CLI).
# Cold-start target: <2 min (FLOWER-10 AC).

# Orchestrator FAB (this repo root) — Grid handoff + kickoff
flwr run . supergrid --stream

# Judge-visible trace
flwr log <run-id> supergrid --show
# Flower Chat activity should show get_nodes → push_messages → pull_messages
```

**FAB note:** root `pyproject.toml` publishes **PoppyOrchestrator** only
(`poppy_orchestrator.agent_app:app`). SuperNode stubs are separate entrypoints
Leandro registers as nodes in the federation (same package, different
`agentapp=` target — or thin sibling FABs that depend on this package).

Config knobs (Orchestrator):

- `fixture-mode=true` — keep until live nodes proven
- `grid-handoff=true` — F0 sample/message before kickoff
- After live nodes: wire `build_grid_clients(agent.grid)` in AgentApp main
  (TODO LEANDRO) and set `fixture-mode` appropriately

## Claim path (orchestrator)

1. **Stub clients** (default dry-run): `StubHospitalCredClient` /
   `StubPayerEnrollmentClient` read shards directly.
2. **Grid clients** (F2/F3 wire): `Grid*Client` → FakeAgentGrid or live
   `agent.grid` → SuperNode claim service reply JSON → `ClaimResponse`.
3. Flow still pauses at HITL (F7); receipt only after Approve (F8).

## Out of scope

- Live hospital EMR / payer / CAQH / NPDB pulls
- Overlapping claim slices between F2 and F3
- Marking FLOWER-10 Done without ≥2 live SuperNodes on SuperGrid
