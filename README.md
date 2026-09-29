# RushPoppy — Flower Labs Hackathon (Stanford 2026-09-29)

Federated US medical provider credentialing claims on Flower SuperGrid + HITL (synthetic MVP).

**Team:** PoppyAI · Demos ~17:15 PT

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

