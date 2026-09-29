# RushPoppy — Flower Labs Hackathon (Stanford 2026-09-29)

Federated US medical provider credentialing claims on Flower SuperGrid + HITL (synthetic MVP).

**Team:** PoppyAI · Demos ~17:15 PT

## Real Flower deployment and human review

Use [the F4 runtime guide](docs/f4-live-runtime.md) for Flower 1.39, two real
SuperNodes, and review in Flower Chat. The coordinator consumes node replies;
missing replies are never replaced with local fixtures. Workers read their own
configured synthetic data files, which are excluded from the FAB. Approval is
an explicit second chat turn and never automatic on this path.

To exercise real local Flower processes on macOS/Linux, run
`uv run python scripts/smoke_local_flower.py`. It starts a TLS SuperLink and two
authenticated SuperNodes, checks the review workflow, and shuts them down.
This automated synthetic test needs no cloud login and does not prove SuperGrid
deployment or a real human approval.

The local dry-run commands below deliberately simulate transport or approval;
they do not establish that a SuperGrid deployment is working.

## Quick start
```bash
# Orchestrator dry-run (no live PHI)
python scripts/dry_run.py
```

## Eng loop
See `docs/ENGINEERING_LOOP.md`: PR → review → Vercel → demo video → bugs → Linear.

## P0 lane (Luigi / CoS)
- F0 Grid tools (≥2 roles)
- F5 PoppyOrchestrator AgentApp
- F6 shared claim contract + HITL gate

Score playbook: `docs/hackathon-score-playbook.md`


## F0 Collaborative AgentApp Grid tools (P0)

Judge-visible SuperGrid handoff Orchestrator ↔ HospitalCred / PayerEnrollment
via Flower `agent.grid` (`get_nodes` sample → `push_messages` → `pull_messages`).

```bash
# Local synthetic dry-run (FakeAgentGrid — no SuperGrid login)
python scripts/run_f0_grid.py
python -m unittest tests.test_f0_grid_tools -v

# SuperGrid (federation must expose HospitalCred + PayerEnrollment SuperNodes)
flwr login supergrid
flwr run . supergrid --stream
# Judge path: Flower Chat activity / flwr log <run-id> supergrid --show
```

Details: `docs/f0-grid-tools.md` · Score playbook: `docs/hackathon-score-playbook.md`

## F5 PoppyOrchestrator kickoff (local)

```bash
# Credential synthetic provider P for network X → HITL → receipt
python -m poppy_orchestrator
python scripts/run_f5.py
python scripts/run_f5.py --provider SYNTH-NPI-1888888888 --hitl escalate

# Unit smoke (stdlib unittest — no pytest required)
python -m unittest tests.test_f5_kickoff -v
```

AgentApp-only FAB (`poppy_orchestrator.agent_app:app`). Synthetic fixtures only.

## F1 claim fixtures (synthetic)

Typed claims: `license_active`, `npi_enumerated`, `exclusion_clear`, `work_history_complete`.

```bash
python -m pytest tests/test_f1_claim_fixtures.py -v
```

SuperNode layout for Leandro: `docs/f1-fixtures.md` → `fixtures/supernodes/{HospitalCred,PayerEnrollment}/`.


## F7 HITL claim review panel

Approve / Escalate / Reject before complete. Auto-approve disabled on panel path.
Happy-path operator decision documented under ~60s. Receipt (F8) only after Approve.

```bash
python scripts/run_f7_hitl.py --serve   # http://127.0.0.1:8765/
python scripts/run_f7_hitl.py --cli
python -m pytest tests/test_f7_hitl_panel.py -v
```

Details: `docs/f7-hitl.md`.

## F8 claim receipt (after Approve)

```bash
python scripts/print_receipt.py
python -m pytest tests/test_f8_claim_receipt.py -v
```

Auditable run-series receipt emits **only** after HITL Approve. See `docs/f8-claim-receipt.md`.


## F2 / F3 SuperNode scaffolds (HospitalCred + PayerEnrollment)

Fixture-backed AgentApp stubs Leandro can register on SuperGrid (live path = FLOWER-10).

```bash
python scripts/run_f2_f3_stubs.py
python -m poppy_orchestrator.supernodes.hospital_cred_app
python -m poppy_orchestrator.supernodes.payer_enrollment_app
python -m pytest tests/test_f2_f3_supernode_stubs.py -v
```

Docs: `docs/f2-f3-supernodes.md` · shards: `fixtures/supernodes/{HospitalCred,PayerEnrollment}/`

## G1 demo runbook + G3 fail-soft

- `docs/g1-demo-runbook.md` — 3–5 min score beats (Flower → problem → HITL → receipt → Hub)
- `docs/g3-failsoft.md` — offline kit when Grid flakes
```bash
python scripts/run_g3_failsoft.py --write
```

## F11 Endeavor (optional bonus)

Endeavor on PoppyOrchestrator claim-assist. Dry-run without API key (`endeavor_optional=true`).

```bash
python -m pytest tests/test_f11_endeavor.py -v
ENDEAVOR_ENABLED=0 python scripts/run_f9_e2e.py --hitl approve
```

Docs: `docs/f11-endeavor.md`

## F9 E2E dry run (demo budget)

```bash
python scripts/run_f9_e2e.py --hitl approve --budget-check
PRIVCRED_E2E_TEST=1 TEST_HITL_DECISION=approve python scripts/run_f9_e2e.py
python -m pytest tests/test_f9_e2e_dry_run.py -v
```

Local stubs only — live SuperGrid dress = G2 (Leandro + Franco). Docs: `docs/f9-e2e-dry-run.md`

## Pitch copy (H1 / H2)

- `docs/h1-competitive-tear-sheet.md` — payer ICP tear-sheet (Symplr cite; no banned claims)
- `docs/h2-why-not-symplr-beat.md` — ≤45s spoken beat
