# G1 — Demo runbook (3–5 min) · FLOWER-16

**Speaker:** Luigi Canoro · **HITL operator:** Franco Petruccelli  
**Window:** demos ~17:15 PT · **Score order:** Flower first → problem → HITL → optional Endeavor → limits

Aligns with `docs/hackathon-score-playbook.md`, `docs/f0-grid-tools.md`,
`docs/f7-hitl.md`, `docs/f8-claim-receipt.md`, `docs/f10-publish-checklist.md`.
Fail-soft cues: `docs/g3-failsoft.md`.

## Pre-flight (T−10 min)

- [ ] `flwr login supergrid` (or confirm offline kit staged — G3)
- [ ] HospitalCred + PayerEnrollment visible in federation (or FakeAgentGrid dry-run ready)
- [ ] HITL panel: `python scripts/run_f7_hitl.py --serve` → http://127.0.0.1:8765/
- [ ] Receipt path smoke: `python scripts/print_receipt.py`
- [ ] Hub / GitHub / Typeform status known (F10 checklist) — say “published” only if true
- [ ] Banned claims card visible to speaker (below)

## Timed beats

### 0:00–0:40 — Flower / SuperGrid handoff *(Use of Flower)*

**Show:** Flower Chat / `flwr log` / `python scripts/run_f0_grid.py` — Orchestrator
samples Grid nodes and messages **HospitalCred** + **PayerEnrollment**.

**Say:** “Two SuperNodes on Flower SuperGrid — hospital credentials and payer
enrollment — exchanging typed verification claims through our PoppyOrchestrator
AgentApp. Grid tools: get nodes, push, pull. Not a chatbot with a logo.”

### 0:40–1:20 — Problem / Symplr wedge *(Impact)*

**Say:** “Payer leaders buy centralized provider data and CVO-style PSV today —
think the Symplr payer-leaders stack. We don’t centralize the dossier. Attributes
stay on SuperNodes; only claims move; a human gates the outcome.”

**Cite (fair use):** https://www.symplr.com/solutions/payer-leaders  
**Do not** steal “75% faster,” “9/10 plans,” or HITRUST-as-ours.

### 1:20–3:00 — Live synthetic claim → HITL → receipt *(Delivery)*

**Show:** Kickoff Provider P (`SYNTH-NPI-1999999999`) → claims aggregate →
Franco clicks **Approve** on the panel (&lt; ~60s) → F8 receipt on screen.

**Say:** “Synthetic provider P for network X. HospitalCred returns work-history;
PayerEnrollment returns license, NPI, exclusion. Human Approve — then an
auditable claim receipt. Escalate and Reject emit no receipt.”

**Commands (local fallback):**

```bash
python scripts/run_f7_hitl.py --serve
# or scripted: python scripts/run_f7_hitl.py --action approve
python scripts/print_receipt.py
```

### 3:00–3:40 — Why Flower + Endeavor *(optional)*

**Say:** “Privacy topology is the business topology — multi-party credentialing
made explicit on Flower.”  
If Endeavor is wired (FLOWER-7): one sentence — “Orchestrator reasoning is on
Endeavor” — then move on. If flaky, skip; Grid + HITL outrank the bonus.

### 3:40–4:30 — Limits + ask

**Say:** “Honest limits: synthetic fixtures only — no live CAQH or NPDB today.
Not a HIPAA-certified or HITRUST product claim. We’re looking for partners with
payer or CVO credentialing pain who want federated claims on Flower.”

## Roles

| Person | Action |
|--------|--------|
| Luigi | Speak beats; point at Grid / Chat |
| Franco | Drive HITL panel; confirm receipt screenshot |
| Leandro | Live SuperNodes / Hub if online; else cue G3 |

## If SuperGrid flakes

Cut to G3 fail-soft kit (`docs/g3-failsoft.md`) — same spoken order with
screenshots. Do **not** invent a live CAQH success.

## Banned claims (never say)

- Live CAQH / NPDB / PHI in this demo
- HITRUST-as-ours / HIPAA-certified product
- Symplr “75% faster” / “9/10 plans” as our numbers
- “We replace Symplr Directory today”
