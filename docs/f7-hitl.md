# F7 — HITL claim review panel (FLOWER-3)

P0 score-critical: **human Approve / Escalate / Reject** before claim completion.
Fail-closed pause from F6 stays mandatory; this surface is what judges click.

## Happy path (operator &lt; ~60s)

1. Kickoff credentialing for synthetic provider P (`SYNTH-NPI-1999999999`).
2. HospitalCred + PayerEnrollment return typed claims (fixtures only).
3. Flow **pauses** at `hitl_pause` / `privcred.hitl.request` — completion blocked.
4. Open the claim panel, skim claims, click **Approve** (typical &lt; 30–60s).
5. **Approve only** → F8 auditable receipt (`privcred.claim_receipt`).
6. Escalate / Reject → outcome updated, **no** receipt.

Documented operator budget: **&lt; 60 seconds** for the happy-path decision.
Auto-approve is **disabled** on the panel path (`auto_approve: false`).

## How to run

```bash
# Judge-visible local web panel
python scripts/run_f7_hitl.py --serve
# → open http://127.0.0.1:8765/  (Approve | Escalate | Reject)

# Interactive CLI panel (re-prompts; empty input rejected)
python scripts/run_f7_hitl.py --cli

# Scripted (CI) — still uses PanelHitlGate, never AutoApproveHitlGate
python scripts/run_f7_hitl.py --action approve
python scripts/run_f7_hitl.py --action escalate
python scripts/run_f7_hitl.py --action reject

python -m pytest tests/test_f7_hitl_panel.py -v
```

Also: `python -m poppy_orchestrator --hitl panel` (console panel).

## Wiring

| Piece | Path |
|-------|------|
| Render / parse | `poppy_orchestrator/hitl/panel.py` |
| Gate + HTTP UI | `poppy_orchestrator/hitl/panel_gate.py` → `PanelHitlGate` |
| Orchestrator pause | `run_credentialing_flow` → `hitl_gate.wait_for_decision` |
| Receipt after Approve | `poppy_orchestrator/receipts/emit.py` (F8) |

`AutoApproveHitlGate` remains **dry-run only** (`--hitl auto`). Live / judge demos
use `--serve`, `--cli`, or `CallbackHitlGate`.

## Constraints (banned claims)

- No live CAQH / NPDB
- Do not claim HITRUST-as-ours or HIPAA-certified UI
- Do not invent “75% faster” copy
- Do **not** skip HITL for demo speed
