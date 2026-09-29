# F10 — Publish checklist (FLOWER-5) — scaffold only

**Status:** engineering scaffold. **Do not mark FLOWER-5 Done** until a human
completes Hub publish + Typeform. This file is a checklist, not a completion proof.

## Republish needed (checked 2026-09-29 13:55 PT)

`@poppyai/privcred-orchestrator` is on Flower Hub as **0.1.0**, published
before the runtime fixes. Downloaded and compared with `main`:

| | Hub 0.1.0 | `main` 0.2.0 |
| --- | --- | --- |
| Runs on SuperNodes | no | yes |
| Review in Flower Chat | no, `hitl-auto-approve-dry-run = "true"` | yes |
| Fixture data inside the FAB | yes | no |
| Conflict case | no | yes |

Anyone who runs the Hub app today runs 0.1.0. To replace it, from a clean
checkout of `main`, logged in as the `poppyai` publisher:

```shell
flwr login supergrid
flwr build
flwr app publish .
```

Then confirm the Hub page lists 0.2.0 and that a fresh
`flwr new @poppyai/privcred-orchestrator` contains
`poppy_orchestrator/live_runtime.py`.

- [ ] 0.2.0 published
- [ ] Hub page shows 0.2.0
- [ ] Typeform entry still points at the right Hub app

## Required (P0 submission gate)

- [ ] **Flower Hub** — publish AgentApp (`flwr app publish .` / Hub docs for
      `poppy_orchestrator.agent_app:app`, AgentApp-only FAB in `pyproject.toml`)
- [ ] **GitHub public** — repo visible:
      https://github.com/poppyia2026-code/FlowerLabsHackathon
- [ ] **Typeform** — submit team entry:
      https://flowerlabs.typeform.com/to/rQuplUGG
- [ ] Hub listing links GitHub (and Typeform if Hub asks)
- [ ] README quickstart matches published FAB / synthetic-only framing

## Owners

- Hub publish run: Leandro Labiano (primary) · Luigi / CoS (config)
- Typeform: human (Luigi / Leandro) — eng cannot complete account steps alone

## Eng may prepare (non-blocking)

- [x] AgentApp-only FAB config in `pyproject.toml`
- [x] Public GitHub remote `poppyia2026-code/FlowerLabsHackathon`
- [ ] Confirm Hub publisher account access (`flwr login` / Hub org)
- [ ] Screenshot Hub listing + Typeform confirmation for board

## Explicitly out of scope for auto-Done

- Marking Linear FLOWER-5 Done without Hub + Typeform evidence
- Claiming HIPAA-certified / HITRUST product status in Hub copy
- Live CAQH/NPDB in Hub demo blurb
