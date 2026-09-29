# F11 — Endeavor model on ≥1 role (FLOWER-7)

**Role wired:** `PoppyOrchestrator` (claim-aggregation assist before HITL)  
**Product:** https://flower.ai/models/endeavor  
**Score:** optional bonus — never blocks Grid tools / HITL / Hub.

## Honesty contract

| Condition | Behavior |
|-----------|----------|
| `FLWR_RUNTIME_BASE_URL` + `FLWR_RUNTIME_API_KEY` (AgentApp) **or** `ENDEAVOR_API_KEY` (+ optional `ENDEAVOR_BASE_URL`) | Live OpenAI-compatible `/responses` call |
| No key / `ENDEAVOR_ENABLED=0` | **Dry-run stub** with `endeavor_optional=true`, `live_call=false` |
| Live call errors | Fall back to stub (`mode=error_fallback`); flow continues to HITL |

**Never** treat dry-run stub text as a production live model call. Events and summaries always carry `endeavor_optional` + `live_call` / `production_live`.

## Model id

Default: `flower/endeavor` (override with `ENDEAVOR_MODEL_ID`).  
Confirm the day-of SuperGrid string in `#hackathon_stanford_2026` if mentors publish a different id — do not invent on stage.

## Where it runs

After `claims_aggregated`, before `hitl_pause`:

1. Build synthetic-only prompt from HospitalCred + PayerEnrollment claims
2. `summarize_claims_for_hitl(...)` via `EndeavorClient`
3. Emit stage `endeavor_assist` + chat text tagged `LIVE` or `DRY-RUN (endeavor_optional)`

## Spoken demo (G1 beat 3:00–3:40)

If live: one sentence — “Orchestrator reasoning is on Endeavor” — then move on.  
If dry-run / flaky: skip aloud; Grid + HITL outrank the bonus.

## Commands

```bash
# Dry-run (no key) — still emits endeavor_assist stage
python scripts/dry_run.py
python scripts/run_f9_e2e.py --hitl approve

# Unit tests (mock / skip live)
python -m pytest tests/test_f11_endeavor.py -v

# Force dry-run even if keys exist
ENDEAVOR_ENABLED=0 python scripts/run_f9_e2e.py --hitl approve
```

## Files

- `poppy_orchestrator/endeavor/` — config, client, summarize
- `poppy_orchestrator/orchestration/flow.py` — `endeavor_assist` stage
- `tests/test_f11_endeavor.py`
- `pyproject.toml` `[tool.flwr.app.config]` — `endeavor-optional = true`

## Out of scope

- Blocking P0 for Endeavor polish
- Live PHI / CAQH / NPDB
- HITRUST-as-ours / HIPAA-certified claims
