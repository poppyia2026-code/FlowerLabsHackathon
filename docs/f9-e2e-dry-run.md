# F9 — E2E dry run in demo budget (FLOWER-14)

**Path:** fixtures → PoppyOrchestrator → HospitalCred + PayerEnrollment claims → HITL → F8 receipt  
**Scope:** **local** stub / FakeAgentGrid dry-run. **Not** live SuperGrid.

## Done when (eng)

- Local script + tests pass
- Machine path completes under ~30s (leaves Franco &lt;60s inside G1 1:20–3:00 beat)
- HITL never silently auto on production path

## Live dress rehearsal

**G2 / Leandro + Franco** — SuperGrid federation, real panel clicks, Hub visibility.  
Do **not** mark FLOWER-14 Done based on live Grid; eng Done = local dry-run + tests.

## HITL auto-driver (CI only)

```bash
# Allowed in tests / CI:
PRIVCRED_E2E_TEST=1 TEST_HITL_DECISION=approve python scripts/run_f9_e2e.py

# Refused without PRIVCRED_E2E_TEST=1 (production never auto):
TEST_HITL_DECISION=approve python scripts/run_f9_e2e.py   # exits non-zero

# Explicit local dry-run preset (not env auto):
python scripts/run_f9_e2e.py --hitl approve
```

## Budget vs G1 beats

| Beat | Wall clock | Notes |
|------|------------|-------|
| 0:00–0:40 Flower handoff | spoken | `run_f0_grid.py` / Chat |
| 0:40–1:20 problem / Symplr | spoken | no machine work |
| 1:20–3:00 claims + HITL + receipt | **machine + Franco** | F9 path must be fast |
| 3:00–3:40 Endeavor optional | spoken | F11 |
| 3:40–4:30 limits + ask | spoken | banned-claims footer |

Machine budget for F9 script: **≤30s** (`--budget-check`).

## Roles

| Person | Action |
|--------|--------|
| Luigi / CoS | Orchestrator path |
| Leandro | SuperNodes / live run (G2) |
| Franco | HITL panel |

## Commands

```bash
python scripts/run_f9_e2e.py --hitl approve --budget-check
PRIVCRED_E2E_TEST=1 TEST_HITL_DECISION=approve python scripts/run_f9_e2e.py --budget-check
python -m pytest tests/test_f9_e2e_dry_run.py -v
```

## Fail-soft

If SuperGrid flakes on G2, cut to `docs/g3-failsoft.md`. Do not invent live CAQH success.
