# RushPoppy sequential eng loop queue
Status · 2026-09-29 ~12:22 PT

## Merged
- PR #1 F6 (FLOWER-8) Done
- PR #2 F5 (FLOWER-6) Done
- PR #3 F0 (FLOWER-4) Done — local FakeAgentGrid; live SuperGrid needs Leandro F4
- PR #4 F0 AC harden (FakeAgentGrid claim-JSON replies) Done
- PR #5 F1 (FLOWER-11) Done — typed claims + SuperNode fixtures (`docs/f1-fixtures.md`)
- PR #6 F8 (FLOWER-13) Done — auditable receipt after Approve only
- PR #7 F7 (FLOWER-3) Done — HITL Approve/Escalate/Reject panel (`docs/f7-hitl.md`)
- PR #8 F2/F3 scaffolds + G1 + G3 (FLOWER-9/12/16/19) **Merged**
- PR #9 F11 Endeavor + F9 E2E + H1/H2 (FLOWER-7/14/17/18) **Merged** — https://github.com/poppyia2026-code/FlowerLabsHackathon/pull/9
- PR #10 H3/H5 + H4 backlog notes (FLOWER-24/21/22/25/27/26/28/29) — pending merge

## Pointer
**Human-gated remaining:** FLOWER-5 Hub+Typeform → FLOWER-10 live ≥2 SuperNodes (Leandro) → FLOWER-20 G2 dress rehearsal (Leandro+Franco).  
**CoS code/docs:** no further CoS-doable business tickets after PR #10. FLOWER-30 eng loop stays In Progress with PR 1–10 summary.

## Sequence remaining (CoS-first)
1. ~~FLOWER-11 F1 fixtures~~ **Done** PR #5
2. ~~FLOWER-13 F8 receipt~~ **Done** PR #6
3. ~~FLOWER-3 F7 HITL panel~~ **Done** PR #7
4. ~~FLOWER-9/12 F2/F3 SuperNode scaffolds~~ **Done** PR #8 — live Grid = FLOWER-10
5. ~~FLOWER-16 G1 runbook~~ **Done** PR #8
6. ~~FLOWER-19 G3 fail-soft~~ **Done** PR #8
7. ~~FLOWER-7 F11 Endeavor~~ **Done** PR #9 (`docs/f11-endeavor.md`)
8. ~~FLOWER-14 E2E F9~~ **Done** PR #9 (local dry-run + tests; live dress = G2)
9. ~~FLOWER-17 H1 tear-sheet~~ **Done** PR #9
10. ~~FLOWER-18 H2 why-not-Symplr~~ **Done** PR #9
11. ~~FLOWER-24 H3 Symplr callout~~ **Done** PR #10 (`docs/h3-symplr-callout.md`)
12. ~~FLOWER-21 H5 payer one-pager~~ **Done** PR #10 (`docs/h5-payer-onepager.md`)
13. ~~FLOWER-22/25/27/26/28/29 H4 backlog~~ **Done** PR #10 (`docs/backlog/`)
14. FLOWER-5 F10 Hub+GitHub+Typeform — **needs human** (Luigi/Leandro); eng scaffolded checklist only — **do not Done**
15. FLOWER-10 F4 live ≥2 SuperNodes (Leandro) — code ready; blocked on flwr login/register — **do not Done**
16. FLOWER-20 G2 rehearsal (Leandro + Franco) — **do not Done**
17. FLOWER-30 eng loop meta — stays **In Progress** (summary comment PRs 1–10)

## Notes
- F9 Done = **local** `scripts/run_f9_e2e.py` + tests — **not** live SuperGrid. Live dress = G2 / Leandro+Franco.
- F11: dry-run without key (`endeavor_optional`); confirm model id day-of in Slack if needed.
- F10 (FLOWER-5): Hub/Typeform publish is human-gated — do not auto-Done.
- Landing is separate repo — H3 callout copy in `docs/h3-symplr-callout.md` only (optional paste into privcred-landing).
- Judge HITL demo: `python scripts/run_f7_hitl.py --serve` → http://127.0.0.1:8765/
- E2E local: `python scripts/run_f9_e2e.py --hitl approve --budget-check`
- G1: `docs/g1-demo-runbook.md` · G3: `docs/g3-failsoft.md` · F2/F3: `docs/f2-f3-supernodes.md`
- Banned claims still in force: live CAQH/NPDB, HITRUST-as-ours, HIPAA-certified, 75% faster.
