# G3 — Fail-soft kit for Grid flake (FLOWER-19)

If SuperGrid / federation flakes before or during demos ~17:15 PT, Delivery
still needs a story: **screenshots + 60–90s spoken fallback** (ties to F4 /
FLOWER-10 fallback).

## Kit contents (repo)

| Artifact | Path |
|----------|------|
| Offline run summary (regen) | `fixtures/g3/offline_demo_summary.json` |
| Spoken fallback script | this file § Spoken fallback |
| Grid handoff cue | `docs/f0-grid-tools.md` + `python scripts/run_f0_grid.py` |
| HITL panel cue | `docs/f7-hitl.md` + `scripts/run_f7_hitl.py --serve` |
| Receipt screenshotables | `fixtures/receipts/example_approve.{txt,json}` |
| G1 beat order | `docs/g1-demo-runbook.md` |

Regenerate offline summary (no SuperGrid):

```bash
python scripts/run_g3_failsoft.py
python scripts/run_g3_failsoft.py --write  # refresh fixtures/g3/
```

## Stage on demo machine

1. Open receipt text: `fixtures/receipts/example_approve.txt`
2. Terminal ready: `python scripts/run_f0_grid.py` (FakeAgentGrid)
3. Optional: HITL panel localhost for Franco
4. Keep this doc + G1 runbook in a second window

## Spoken fallback (60–90s)

> “If the live SuperGrid link is slow, here’s the same path offline. Orchestrator
> samples HospitalCred and PayerEnrollment on Flower’s Grid tool surface —
> get nodes, push claims, pull replies — synthetic only. Claims aggregate, a
> human Approves on the panel, and we emit an auditable receipt. Architecture
> is federated claims, not a centralized dossier. Limits: fixtures only; no live
> CAQH or NPDB; we are not claiming HITRUST or HIPAA-certified product status.
> Happy to show the Hub listing and GitHub next.”

## Operator cues

- Prefer **live** Grid if it recovers mid-slot; otherwise stay on kit — don’t
  thrash login on stage.
- Never pretend a live payer pull succeeded.
- Link from FLOWER-10 / F4: fallback = this kit.

## Out of scope

- Inventing Symplr % in the fallback
- HITRUST-as-ours
- Live CAQH/NPDB “success” screenshots
