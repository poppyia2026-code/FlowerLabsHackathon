# F13 — Stayed vs Traveled (FLOWER-34)

Privacy wedge for demos: each SuperNode holds a synthetic `local_record`
(~15–40 leaf fields). Only typed claims leave the node. The HITL panel and
G3 kit show both columns with **run-derived** counts.

## Data path

1. SuperNode fixtures (`fixtures/supernodes/*/providers.json`) include
   `local_record` (synthetic dossier; never the traveled payload).
2. Stub clients attach `privacy_summary` on `ClaimResponse`:
   - `stayed_field_count` — leaf count of `local_record`
   - `stayed_preview` — field paths (names only)
   - `traveled_claim_count` — number of typed claims in the reply
3. `poppy_orchestrator/hitl/stayed_traveled.py` builds the view from the
   ClaimBundle / reply JSON **already in memory** (no new network calls).
4. F7 panel embeds the F13 block; G3 writes screenshotables under
   `fixtures/g3/stayed_vs_traveled.{html,json}`.

## Regen G3 artifact

```bash
python scripts/run_g3_failsoft.py --write
```

## Out of scope / banned

- HIPAA / HITRUST wording as ours
- Real records / live CAQH / NPDB
- Hard-coded “23 fields stayed” — counts must come from the run
