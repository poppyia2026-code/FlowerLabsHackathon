# G1b — Demo runbook v2 (problem-first + conflict) · FLOWER-35

**Speaker:** Luigi Canoro · **HITL operator:** Franco Petruccelli  
**Window:** demos ~17:15 PT · **Rehearse:** G2 (FLOWER-20) against this v2  
**Supersedes:** G1 (FLOWER-16) spoken order — keep fail-soft cues in `docs/g3-failsoft.md`

Aligns with `docs/f12-conflicting-claims.md`, `docs/f7-hitl.md`, `docs/f8-claim-receipt.md`,
`docs/f11-endeavor.md`, `docs/hackathon-score-playbook.md`.

**Spoken path change:** open on the problem; drop the Symplr beat from the talk track
(Symplr stays in deck/landing callouts only — H1–H3).

## Pre-flight (T−10 min)

- [ ] `flwr login supergrid` (or offline kit staged — G3)
- [ ] HospitalCred + PayerEnrollment visible (exact names) with **updated** `poppy-data`
      fixtures that include conflict providers R/S (see `docs/f12-conflicting-claims.md`)
- [ ] Flower Chat two-run HITL ready (`/approve`, `/escalate`, `/reject` with run id)
- [ ] Happy path provider P and conflict provider R (explained) + S (unresolved) known
- [ ] Receipt smoke: `python scripts/print_receipt.py`
- [ ] If F13 (FLOWER-34) shipped: stayed-vs-traveled view open; else use spoken cut line
- [ ] Banned claims card visible to speaker (below)
- [ ] Hub / GitHub / Typeform status known — say “published” only if true

## Timed beats (target ~4:00)

### 0:00–0:20 — Problem *(one sentence)*

**Say:** “A newly hired doctor typically cannot bill for three to four months because
the hospital and the payer do not pass each other the paperwork — the records stay
siloed.”

**Do not** open with Flower plumbing or a Symplr name-drop.

### 0:20–1:20 — Live SuperGrid happy path *(Use of Flower + Delivery)*

**Show:** Flower Chat / SuperGrid — PoppyOrchestrator asks **HospitalCred** and
**PayerEnrollment**; only typed yes/no claims leave each node.

**Kickoff (Chat):**

```text
Verify SYNTH-NPI-1999999999 for SYNTH-NETWORK-X
```

**Say:** “Two organizations on Flower SuperGrid answer. Nothing but verification claims
leaves them — not the dossier. Franco will gate the outcome in Chat.”

**Operator:** `/approve run-<id>` after claims aggregate (happy path; sources agree).

**Cut if slow:** skip spoken detail; keep Grid visible; move to conflict if happy path
already screenshotable from rehearsal.

### 1:20–2:40 — Conflict beat *(F12)*

**Show:** Agents disagree → orchestrator re-asks the owner once → person decides in
Flower Chat.

**Prefer explained (R) then refuse-approve on unresolved (S) if time:**

```text
Verify SYNTH-NPI-1777777777 for SYNTH-NETWORK-X
/approve run-<id>
```

```text
Verify SYNTH-NPI-1666666666 for SYNTH-NETWORK-X
/approve run-<id>          (refused — review stays pending)
/escalate run-<id> seven month gap
```

**Say:** “Payer sees a gap; hospital is asked again with only that disputed period.
If they explain it, we can approve. If it stays unresolved, Chat refuses approve —
escalate or reject. One re-ask, then a human.”

**Cut lines:** If live SuperNodes lack R/S fixtures, say so and run FakeAgentGrid /
local Flower smoke for the same providers — never invent live CAQH success.
If only one conflict fits the clock, run **R** (explained → approve) and name **S**
as the refuse-approve path.

### 2:40–3:20 — Receipt + stayed vs traveled

**Show:** Auditable receipt after Approve only (`docs/f8-claim-receipt.md`).

**Say:** “Approve emits a receipt you can screenshot. Escalate and reject do not.”

**Stayed vs traveled (F13 / FLOWER-34):** If the view is live, show two columns per
node (fields that stayed vs claims that traveled) and one number line
(“N fields stayed, K yes/no answers traveled”).

**Cut line if F13 not merged:** “Privacy claim: the full record stays on each
SuperNode; only the typed answers traveled. We’re shipping the side-by-side view
next — same numbers from the fixtures.”

### 3:20–4:00 — Own models + limits + ask

**Say:** “Each organization can run its own model — Endeavor on a role, Nebius on a
node when wired — and they still collaborate on the Grid. Honest limits: synthetic
fixtures only; no live CAQH or NPDB; we are not claiming HITRUST or HIPAA-certified
product status. Looking for partners with payer or hospital credentialing friction
who want federated claims on Flower.”

**Cut if Endeavor/Nebius not live:** one sentence on “own model per org” architecture,
then limits + ask. Do not claim a live Nebius node unless FLOWER-36 is actually up.

## Roles

| Person | Action |
|--------|--------|
| Luigi | Speak beats; point at Chat / Grid / receipt |
| Franco | Drive Chat HITL (`/approve` `/escalate` `/reject`); confirm receipt |
| Leandro | Live SuperNodes + updated `poppy-data` for R/S; else cue G3 |

## If SuperGrid flakes

Cut to G3 fail-soft kit (`docs/g3-failsoft.md`) — same problem-first order with
screenshots. Do **not** invent a live CAQH success. Prefer FakeAgentGrid conflict
fixtures over silence.

## Banned claims (never say)

- Live CAQH / NPDB / PHI in this demo
- HITRUST-as-ours / HIPAA-certified product
- Vendor “75% faster” / “9/10 plans” as our numbers
- “We replace Symplr Directory today”
- Opening with Symplr as the spoken problem (deck/landing only)

## G2 timing note

This file is the v2 script. Live wall-clock timing lands in dress rehearsal
FLOWER-20 (G2) — check boxes there after one timed pass.
