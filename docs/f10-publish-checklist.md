# F10 — Publish checklist (FLOWER-5 / FLOWER-37) — scaffold only

**Status:** engineering scaffold. **Do not mark FLOWER-37 Done** until a human
publishes 0.2.0 under `leanlabiano` and confirms the Hub page. This file is a
checklist, not a completion proof.

## Republish needed (updated 2026-09-29 15:50 PT)

Team decision (Franco + Leandro): publish under **`leanlabiano`**, not `poppyai`.
Nobody at the table can sign in as `poppyai`. Flower rejects uploads when
`publisher` ≠ signed-in account (`403 publisher does not match authenticated user`).

| | Hub `@poppyai/...` 0.1.0 (legacy) | Target `@leanlabiano/...` 0.2.0 |
| --- | --- | --- |
| Runs on SuperNodes | no | yes |
| Review in Flower Chat | no (`hitl-auto-approve-dry-run = "true"`) | yes |
| Fixture org data inside the FAB | yes | no (loader `.py` only) |
| Conflict case | no | yes |

Do **not** show or link the old `@poppyai/privcred-orchestrator` 0.1.0 page.

From a clean checkout of `main` with `publisher = "leanlabiano"`, logged in as
Leandro:

```shell
uvx flwr@1.39.0 login supergrid
uvx flwr@1.39.0 app publish .
```

Then confirm:

- https://flower.ai/apps/leanlabiano/privcred-orchestrator lists **0.2.0**
- Code tab shows `poppy_orchestrator/live_runtime.py`
- Federation `@leanlabiano/rushpoppy`: Manage agents → add the new Hub app
- Typeform / slides point at `@leanlabiano/...` (not `@poppyai/...`)

- [ ] 0.2.0 published as `@leanlabiano/privcred-orchestrator`
- [ ] Hub page shows 0.2.0 + `live_runtime.py`
- [ ] Typeform / slides updated to leanlabiano Hub URL
- [ ] Federation agent entry switched from local build to Hub app

## Required (P0 submission gate)

- [ ] **Flower Hub** — publish AgentApp (`flwr app publish .` / Hub docs for
      `poppy_orchestrator.agent_app:app`, AgentApp-only FAB in `pyproject.toml`)
- [x] **GitHub public** — repo visible:
      https://github.com/poppyia2026-code/FlowerLabsHackathon
- [ ] **Typeform** — entry Hub URL matches leanlabiano app
- [ ] Hub listing links GitHub
- [ ] README quickstart matches published FAB / synthetic-only framing

## Owners

- Hub publish run: Leandro Labiano (signed-in publisher) · CoS (publisher line on main)
- Typeform / slides URL flip: human (Luigi / Leandro)

## Eng may prepare (non-blocking)

- [x] AgentApp-only FAB config in `pyproject.toml`
- [x] `publisher = "leanlabiano"` on main (FLOWER-37)
- [x] Public GitHub remote `poppyia2026-code/FlowerLabsHackathon`
- [ ] Confirm Hub 0.2.0 after Leandro `flwr app publish`
- [ ] Screenshot Hub listing + Typeform confirmation for board

## Explicitly out of scope for auto-Done

- Marking Linear FLOWER-37 Done without Hub 0.2.0 evidence under leanlabiano
- Claiming HIPAA-certified / HITRUST product status in Hub copy
- Live CAQH/NPDB in Hub demo blurb
