# F0 — Collaborative AgentApp Grid tools (≥2 roles)

**Runtime update:** [F4 live runtime](f4-live-runtime.md) replaces the two-stage
handoff plus local-fixture lookup with actual Grid-backed claim clients. This
document's standalone F0 script remains an offline diagnostic. Automatic
approval is not available in the deployed AgentApp; use the Flower Chat review.

Score playbook P0: judges must see live SuperGrid collaboration via Flower
**Collaborative AgentApp Grid tools** (`agent.grid` sample / message) between
≥2 roles — not a lone chatbot.

## Roles

| Role | Grid name | Slice |
|------|-----------|-------|
| Orchestrator | `PoppyOrchestrator` | Kickoff + aggregate + HITL |
| HospitalCred | `HospitalCred` | Education / work-history / board claims |
| PayerEnrollment | `PayerEnrollment` | NPI / license / exclusion / enrollment |

## Tool path (Flower RuntimeAgentGrid)

1. `get_nodes(sample_size=…)` — sample SuperNodes (federation roster)
2. `push_messages([...])` — Orchestrator → each role with synthetic claim request
3. `pull_messages(message_ids, timeout)` — collect ACK / claim payloads

Events: `privcred.stage` (`grid.get_nodes`, `grid.push_messages`, …) +
`privcred.message` for Flower Chat / `flwr log`.

## Local dry-run (no SuperGrid)

```bash
python scripts/run_f0_grid.py
python -m unittest tests.test_f0_grid_tools -v
```

Uses `FakeAgentGrid` with synthetic HospitalCred + PayerEnrollment nodes.

## SuperGrid / `flwr run`

```bash
# Once Leandro has ≥2 SuperNodes named HospitalCred + PayerEnrollment
# registered in the federation:
flwr login supergrid
flwr run . supergrid --stream

# Flower Chat (browser or CLI) — select PrivCred PoppyOrchestrator
flwr chat

# Judge-visible logs
flwr log <run-id> supergrid --show
```

Config (`pyproject.toml` / `--run-config`):

- `grid-handoff=true` — run F0 before F5 kickoff (default)
- `grid-pull-timeout=30` — seconds to await SuperNode replies
- `fixture-mode=true` — synthetic claim clients (keep until live nodes ready)
- `hitl-auto-approve-dry-run=true` — dry-run only; live path fail-closed (F6)

## Constraints

- AgentApp-only FAB — **do not** add ServerApp/ClientApp
- Synthetic fixtures only — no live CAQH / NPDB / PHI
- Never skip HITL on the complete path (F6)

## Refs

- Score playbook: `docs/hackathon-score-playbook.md`
- AgentGrid API: https://flower.ai/docs/framework/ref-api/flwr.agentapp.AgentGrid.html
- AgentApp runtime: https://flower.ai/docs/agent/explanations/agentapp-runtime.html
- Collab template: https://flower.ai/apps/flwrlabs/collaborative-agent
- Hackathon recipe: https://github.com/jafermarq/flower-collaborative-agent-hackathon
