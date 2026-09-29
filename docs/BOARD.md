# PoppyAI / PrivCred — Linear board seed (Flower Stanford, 2026-09-29)

**Workspace:** https://linear.app/poppyai  
**Product:** PrivCred — federated provider credentialing on Flower SuperGrid  
**MVP in:** HospitalCred + PayerEnrollment SuperNodes → PoppyOrchestrator → HITL → claim receipt (synthetic only)  
**MVP out:** live CAQH/NPDB, HIPAA-certified claims, HITRUST claims  
**Wedge (post-demo / business):** Compete for **payer-leader** budget vs [symplr solutions for payer leaders](https://www.symplr.com/solutions/payer-leaders) — federated credentialing/enrollment **claims** on Flower vs symplr’s centralized PDM/CVO/Directory/Compliance stack  
**Humans:** Luigi Canoro · Leandro Labiano · Martín Pulido · Franco Petruccelli  
**Demo window:** ~17:15 PT  
**Updated:** 2026-09-29 ~11:05 PT — Score playbook tickets: P0 Grid tools + Endeavor + Hub publish  
**Status:** Markdown seed for CoS / Linear web (MCP not connected). Do not invent API credentials.  
**Score playbook (authoritative for P0/bonus):** `/workspace/poppy-privcred-research/hackathon-score-playbook.md`  
**Research pack:** `/workspace/poppy-privcred-research/{team-brief-v0.md,pack-v1.md,sources.json}`  
**Orchestrator WIP (CoS):** `/workspace/privcred-orchestrator/`

Labels: `epic`, `research`, `pitch`, `slides`, `design`, `landing`, `build`, `demo`, `business`, `post-demo`, `blocker`, `synthetic-only`, `luigi-lane`, `leandro`, `franco`

---

## Assignee map (Build/Dev)

| Person | Lane | Tickets |
|--------|------|---------|
| **Leandro Labiano** | SuperNodes + federation + Hub | F0 (co), F2, F3, F4, F9 (run), F10, F11 (opt) |
| **Luigi Canoro** | Coding via **CoS only** + narrative | F0 (co), F5, F6 (lead), F11 (opt); speak demo |
| **Franco Petruccelli** | Fixtures · HITL · receipt · fail-soft | F1, F7, F8, G1 (co), G3 |
| **Martín Pulido** | **Not on Build** (per Luigi) | TBD outside Build unless Luigi overrides |
| Agents | Research / Pitch / Slides / Design / Landing / Business | Rita / Pablo / Sofia / Diego / Leo |

---

## Epic A — Research
Owner: Rita Research Poppy · sponsor: Luigi  
**Status:** Pack landed — mark A1–A5 Done when seeding Linear.  
Paths: `/workspace/poppy-privcred-research/`

---

## Epic B — Pitch
Owner: Pablo Pitch Poppy · speaker: **Luigi**  
B1 Spoken script · B2 One-pager · B3 QA vs research  
*(Also pull H2 “why not Symplr” beat into script if time.)*

---

## Epic C — Slides
Owner: Sofia Slides Poppy · sponsor: Luigi  
C1 Structure · C2 Deck v1 · C3 Polish + notes  
*(Also H3 competitor callout slide.)*

---

## Epic D — Design
Owner: Diego Design Poppy  
D1 Brand kit · D2 UI mocks (kickoff → claims → HITL → receipt) · D3 Handoff

---

## Epic E — Landing
Owner: Leo Landing Poppy · sponsor: TBD (not Martín unless Luigi directs)  
E1 Landing + Hub shell · E2 Demo CTA · E3 Copy QA  
*(Also H3 landing competitor callout.)*

---

## Epic F — Build / AgentApp (MVP) — PRIORITY 1

**Score playbook:** `/workspace/poppy-privcred-research/hackathon-score-playbook.md`  
Judging: Use of Flower (Agents + SuperGrid) · Impact · Demo/Delivery · **Endeavor bonus**.  
**P0 (must on screen):** Collaborative AgentApp **Grid tools** (`agent.grid` sample/message) between ≥2 roles + HITL + **Flower Hub publish** (+ GitHub + Typeform).

```
PoppyOrchestrator (AgentApp) — Collaborative Grid tools
  → SuperNode HospitalCred claims
  → SuperNode PayerEnrollment claims
  → HITL (Approve / Escalate / Reject)
  → auditable claim receipt
```

Hackathon stays **synthetic**. Do not implement live Symplr/CAQH/NPDB integrations in F*.  
Anti-patterns (lose Use-of-Flower): single chatbot with logo only; mixing ServerApp/ClientApp FL story; live scrapers / HIPAA claims.

### F0. Collaborative AgentApp Grid tools (P0) — **Luigi / CoS** + **Leandro** · label `build` `luigi-lane` `leandro` `P0`
**Playbook:** Must show live SuperGrid collaboration via official **Flower Collaborative AgentApp** Grid tools (`agent.grid` sample / message) between ≥2 roles (Orchestrator ↔ HospitalCred / PayerEnrollment).  
**AC:**
- Based on Flower Collaborative AgentApp / Grid tools template (not a lone chatbot)
- Visible Grid sample/message handoff between ≥2 roles on SuperGrid (`flwr run . supergrid --stream` or equivalent)
- Judge-visible in Flower Chat activity / `flwr log`
- AgentApp-only FAB (no ServerApp/ClientApp mix)
- Ties into F5 Orchestrator + F2/F3 nodes

### F1. Claim schema + synthetic fixtures — **Franco**
**AC:** Typed claims (`license_active`, `npi_enumerated`, `exclusion_clear`, `work_history_complete`); synth provider P; happy + escalate paths; no live pulls; path agreed with Leandro

### F2. SuperNode HospitalCred — **Leandro**
**AC:** Synth education/work-history/privileges stub; claims only; federation-ready; trace visible

### F3. SuperNode PayerEnrollment — **Leandro**
**AC:** Synth NPI/license/exclusion; returns license/npi/exclusion claims; disjoint slice from F2

### F4. Federation bring-up — **Leandro**
**AC:** ≥2 SuperNodes on SuperGrid; cold-start <2 min; fallback → G3

### F5. PoppyOrchestrator AgentApp — **Luigi / CoS** (`luigi-lane`)
**AC:** Kickoff credential P for network X; fetch both nodes; emit events; pause for HITL; AgentApp-only FAB  
**WIP:** `/workspace/privcred-orchestrator/`

### F6. Orchestrator ↔ node claim contract — **Luigi / CoS** + Leandro review
**AC:** Shared request/response; fail if node missing; never skip HITL; scripted fixture test

### F7. HITL review surface — **Franco**
**AC:** Claim panel; Approve / Escalate / Reject; required before complete; <60s

### F8. Claim receipt — **Franco** (+ Luigi/CoS emit hook)
**AC:** After Approve, auditable run-series receipt; screenshotable

### F9. E2E dry run — Leandro (run) · Franco (HITL) · Luigi/CoS (orchestrator)
**AC:** fixtures → Orchestrator → 2 claims → HITL → receipt in demo budget

### F10. Flower Hub publish + submission gate (P0) — **Leandro** · **Luigi / CoS** config · label `build` `P0` `demo`
**Playbook:** Submission gate = **Published Flower Hub AgentApp + GitHub + Typeform** before ~17:15 PT.  
**AC:**
- AgentApp published to **Flower Hub** (Hub instructions from playbook / Flower docs)
- Public **GitHub** repo linked from Hub / README
- **Typeform** https://flowerlabs.typeform.com/to/rQuplUGG completed (lowercase L — not rQupIUGG)
- Stable Hub app id / URL for demo machine; README cold-start <2 min
- `flwr login supergrid` path documented for judges/team

### F11. Endeavor model bonus (P1) — **Luigi / CoS** or **Leandro** on one node · label `build` `bonus` `luigi-lane`
**Playbook:** Optional but explicit **Endeavor** bonus — model on at least one agent/node; agent performance informs judges but is not decisive.  
**AC:**
- Endeavor wired into ≥1 role (prefer PoppyOrchestrator or one SuperNode claim path)
- Mentioned in spoken demo if used (script beat 3:00–3:40)
- Does not block P0 Grid tools / HITL / Hub if time-crunched — cut last
- Synthetic-only prompts/fixtures; no live PHI

---

## Epic G — Demo prep — PRIORITY 1
**Playbook demo order:** Flower handoff first → problem/Symplr wedge → live HITL → Endeavor mention if used → limits + ask.  
G1 Runbook — Luigi + Franco (match playbook 3–5 min beats)  
G2 Dress rehearsal — lead Luigi  
G3 Fail-soft kit — Franco  

---

## Epic H — Business wedge vs Symplr (payer leaders) — POST-DEMO / BUSINESS

**Score + business playbook:** `/workspace/poppy-privcred-research/hackathon-score-playbook.md` (business thesis + demo script order + Symplr wedge)  
**Primary cite:** [Healthcare Payer Solutions | symplr](https://www.symplr.com/solutions/payer-leaders)  
**Luigi pivot:** Compete for the same **payer-leader** buyers symplr targets (Network Management, Credentialing, Executive leaders on that page), with a *different architecture*: federated credentialing/enrollment **claims** on Flower SuperGrid instead of a centralized payer Operations Platform.

### What symplr sells on that page (cite-accurate, no invented %)
- Integrated **Operations Platform** for payers: provider data management, credentialing, clinical decision support, compliance
- Positioning: single source of truth; reduce redundancy; automate PSV; network adequacy / directory; HITRUST r2 for symplr Payer; NCQA-accredited CVO services; Hayes Knowledge Center; Compliance suite
- Marketing claims on page (do **not** reuse as ours): “9 out of 10 health plans,” “75% faster credentialing,” “#1 Client-rated” Black Book 2024, “only HITRUST-certified payer solution”

### PrivCred counter-position (safe)
| Incumbent (symplr-class) | PrivCred / PoppyAI |
|--------------------------|--------------------|
| Centralize provider data (PDM / SSOT) | Attributes stay on SuperNodes; only typed verification claims move |
| Outsourced CVO does PSV | HITL + multi-party claim protocol (demo = synthetic) |
| HITRUST / enterprise compliance story | **Do not claim** HITRUST, HIPAA certification, or BAAs today |
| Directory + network steering | Future post-demo: enrollment/network claim types — not MVP |

**Hard rule:** Hackathon MVP remains synthetic (Epic F). Epic H tickets are **post-demo / business** unless explicitly marked “demo beat only.”

### H1. Competitive tear-sheet (payer ICP) — Rita · label `business` `post-demo`
**AC:**
- 1-pager mapping symplr payer modules (PDM, CVO/PSV, Directory, Hayes, Compliance) → PrivCred federated-claims wedge
- ICP bullets from Symplr page roles: Network Management / Credentialing / Executive leaders
- Cite https://www.symplr.com/solutions/payer-leaders ; no invented $ or %; no HITRUST-of-us claims
- Path under `/workspace/poppy-privcred-research/` or `/workspace/poppy-privcred-tickets/`

### H2. Pitch beat “why not just Symplr?” — Pablo · label `pitch` (demo-safe if ≤45s)
**AC:**
- 30–45s spoken beat: centralized dossier vs SuperGrid claims + HITL
- Optional in B1 if timing allows; otherwise post-demo sales script
- No “we’re HITRUST” / no stealing “75% faster”

### H3. Slide + landing competitor callout — Sofia + Leo · `slides` `landing` `post-demo` (or light demo)
**AC:**
- One slide / landing section: “Incumbents centralize; we make distribution explicit on Flower”
- Name Symplr as category example with fair-use link to payer-leaders page
- Does not block 17:15 PT if cut for time

### H4. Post-demo product backlog (payer enrollment / network) — Tomás + Luigi · `business` `post-demo`
**AC:** Linear-ready backlog issues (clearly **not** MVP):
- H4a. Payer-enrollment claim types beyond MVP flags (network participation, specialty/location assignment metaphors — synthetic first)
- H4b. Multi-payer federation story (N hospital nodes × M payer nodes)
- H4c. Audit-export / compliance packet from run-series events (competes with “compliance visibility,” not a GRC suite claim)
- H4d. Directory-lite future (member steering) — explicitly later; do not imply we replace symplr Directory
- H4e. Security/compliance roadmap note: path toward enterprise assurances **without** claiming HITRUST today

### H5. One-pager “PrivCred for payer leaders” (sales) — Connie or Pablo + Luigi · `business` `post-demo`
**AC:**
- Buyer one-pager aimed at same ICP as Symplr payer page
- Problem (siloed/centralized PDM friction + privacy) → Flower SuperGrid claims → HITL governance
- Clear MVP vs roadmap; cite Symplr page as competitive context

### H6. Seed Epic H in Linear — CoS · when web/MCP auth works
**AC:** Create Epic H + H1–H5 (and H4a–e as children or checklist); return issue URLs to Tomás

---

## Priority cut

| When | What |
|------|------|
| **P0 (score-critical)** | **F0** Grid tools · HITL (F7) · **F10** Hub+GitHub+Typeform · live ≥2-role SuperGrid handoff |
| **P1 before ~17:15 PT** | F1–F9, B1 (Flower-first script), G1–G3, C2; **F11 Endeavor** if time; optional H2 |
| **P2** | E1–E2, D1–D2, B2, H1 |
| **P3 / post-demo** | H3–H5, H4 backlog |

---

## Luigi-only tickets (CoS executes)

1. **F0** Collaborative AgentApp Grid tools (P0) — with Leandro on nodes  
2. **F5** PoppyOrchestrator AgentApp — `/workspace/privcred-orchestrator/`  
3. **F6** Orchestrator ↔ node claim contract  
4. **F11** Endeavor bonus (optional / P1) — if time after P0  

Coordinate only: F8 emit hook, F9/F10 Hub publish with Leandro/Franco.  
**No Martín on F\*.**

---

## Seeding checklist (CoS / Linear web)

1. Project **PrivCred Flower Stanford 2026-09-29**
2. Epics **A–H** (H = business / Symplr wedge)
3. Assignees: Leandro F0(co),F2–F4,F9,F10 · Luigi/CoS F0,F5,F6,F11 · Franco F1,F7,F8,G1,G3 · Martín none on Build
4. Mark research Done; link research + **score playbook** + this BOARD
5. Create H1–H6 with Symplr cite; create **F0, F10 (Hub gate), F11 (Endeavor)** explicitly

**Board path:** `/workspace/poppy-privcred-tickets/BOARD.md`

— Tomás Tickets Poppy · cite: https://www.symplr.com/solutions/payer-leaders · no invented credentials
