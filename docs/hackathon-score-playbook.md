# RushPoppy — Hackathon score + Symplr business playbook
Stanford Flower · 2026-09-29 · demos ~17:15 PT

## Judging (official)
1. **Use of Flower** — Agents + SuperGrid collaboration (primary theme)
2. **Impact & Originality** — unique value
3. **Demo & Delivery** — clarity of approach + working result  
Bonus: **Endeavor** model. Agent performance informs but is not decisive.

## Business thesis (post-demo + pitch impact)
**ICP:** Payer leaders (Network / Credentialing / Exec) currently buying **symplr Payer** stack (PDM single source of truth, CVO PSV outsourcing, Directory, Hayes, Compliance).  
**Wedge:** Don’t be a cheaper CVO. Sell **federated verification claims** — hospital/payer SuperNodes keep attributes local; PoppyOrchestrator + HITL make multi-party credentialing/enrollment explicit on Flower.  
**Never claim today:** HITRUST, “75% faster,” HIPAA-certified, live CAQH/NPDB.

## Max points — what MUST be on screen
| Must | Why |
|------|-----|
| Live **SuperGrid** run with **≥2 agents/nodes** handoff | Use of Flower |
| **Collaborative AgentApp** Grid tools (`agent.grid` sample / message) | Official challenge wording |
| **HITL** pause before final status | Safe collaboration theme |
| **Published Flower Hub** AgentApp + GitHub + Typeform | Submission gate |
| Spoken path: Flower first → problem → result | Demo criterion |
| Optional: **Endeavor** model in at least one node | Explicit bonus |

## Flower Labs assets to use TODAY
- Docs: write-your-first-agentapp, collaborative research agent, run-on-supergrid, connectors
- Templates: **Flower Collaborative AgentApp** (Grid tools) + Hub AgentApp template
- `flwr login supergrid` · `flwr chat` · `flwr run . supergrid --stream`
- Slack `#hackathon_stanford_2026` (Nebius keys, mentors, credits)
- Nebius SuperNode path if mentors push multi-node GPU (else SuperGrid-hosted agents)
- Flower Chat activity / `flwr log` for judge-visible handoffs
- Publish: Hub instructions before 17:15

## Demo script order (3–5 min) — score optimized
1. **0:00–0:40** SuperGrid handoff visible (HospitalCred ↔ PayerEnrollment via Orchestrator) — *Use of Flower*
2. **0:40–1:20** Problem: payer credentialing / network onboarding pain; Symplr centralizes; we federate claims — *Impact*
3. **1:20–3:00** Live synthetic claim → HITL Approve → receipt — *Delivery*
4. **3:00–3:40** Why Flower (privacy topology = business topology) + Endeavor mention if used
5. **3:40–4:30** Limits honest + ask (partners with payer/CVO pain)

## Build priority (points > polish)
P0: Collaborative AgentApp on SuperGrid with Grid sample between ≥2 roles + HITL + Hub publish  
P1: Endeavor on one agent; run-event panel Franco  
P2: Landing/deck Symplr callout; Nebius multi-SuperNode only if mentors make it easy

## Anti-patterns (lose Use-of-Flower points)
- Single chatbot with “Flower” logo only
- Mixing ServerApp/ClientApp FL training story instead of AgentApp collaboration
- Live scrapers / HIPAA claims (hurts trust + originality)

---

## Rita delta
**Author:** Rita Research Poppy · **Updated:** 2026-09-29 ~11:15 PT  
**Rule:** Append-only enrichment of the CoS body above — do not delete CoS content.  
**Sources:** Symplr payer-leaders (fetched); Stanford discuss post + warmup links; Flower Agent docs / Hub / Endeavor.

### 1. Deeper Symplr payer-leaders wedge (Impact beat)

**Primary:** https://www.symplr.com/solutions/payer-leaders

**What Symplr sells to payer leaders (paraphrase, cite-accurate):**
| Module | Capability (safe paraphrase) | Cite |
|--------|------------------------------|------|
| **Operations Platform / PDM** | End-to-end provider data management; **single source of truth**; kill silos/redundancy; automate repetitive tasks | payer-leaders |
| **symplr Payer** | Automated PSV, compliance tracking (CMS/NCQA/No Surprises Act — *vendor claim*), centralized provider data, claims/enrollment/member interoperability, audit reports | https://www.symplr.com/products/symplr-payer |
| **symplr Directory** | Governed directory / network data; member steering; integrated with Payer | https://www.symplr.com/products/symplr-directory · payer-leaders |
| **NCQA CVO / PSV services** | Outsourced primary source verification, expirables, ongoing monitoring, backlog fill; committee-ready files | payer-leaders · https://www.symplr.com/products/symplr-cvo |
| **Hayes Knowledge Center** | Clinical evidence for coverage / UM / appeals | payer-leaders |
| **symplr Compliance** | Holistic payer compliance program tooling | payer-leaders |
| **ICP personas on page** | Network Management · Credentialing · Executive leaders | payer-leaders |

**vs RushPoppy (hackathon):** Symplr **centralizes** dossiers into SSOT + optionally **outsources** PSV to a CVO (incl. CAQH enrollment on CVO page). RushPoppy demos **distributed verification made explicit**: Flower SuperGrid multi-agent handoff; attributes stay on SuperNodes; only typed **verification claims** move; synthetic fixtures + HITL; **not** a CVO/CAQH clone.

**Safe one-liners (pitch/slides may use):**
- “Symplr’s payer stack centralizes provider data and automates or outsources PSV; RushPoppy shows the multi-party claim protocol on Flower without centralizing the file.”
- “Same buyer pain (payer credentialing / network readiness) — different architecture: federated claims + HITL vs PDM/CVO SSOT.”
- “Demo is synthetic: claims only, human gate, SuperGrid-visible handoff.”

**Banned overclaims (never say):**
- Any Symplr marketing % as ours or as independent fact: “9/10 plans,” “75% faster / less time on PSV,” Black Book “#1,” “only HITRUST payer solution”
- RushPoppy is HITRUST / HIPAA-certified / BAA-ready / production CVO
- Live CAQH, NPDB, or PHI scrapers in the demo
- “We’re replacing Symplr today” / invented market share

Full tear-sheet: `symplr-payer-wedge.md` · pack Section B: `pack-v1.md`

### 2. Exact Flower Labs asset URLs (copy-paste)

**Official day-of + submit**
- Discuss (schedule, challenge, judging, bonus): https://discuss.flower.ai/t/collaborative-agent-hackathon-stanford-ca-2026/1275
- **Team submission Typeform:** https://flowerlabs.typeform.com/to/rQuplUGG
- Event page: https://flower.ai/events/collaborative-agent-hackathon-stanford-2026
- Slack join: https://flower.ai/join-slack → `#hackathon_stanford_2026`

**Warmup docs (linked from discuss)**
- Agent docs home: https://flower.ai/docs/agent/
- Quickstart: https://flower.ai/docs/agent/tutorials/quickstart.html
- Get started / Chat: https://flower.ai/docs/agent/tutorials/get-started-with-flower-agent.html
- Write your first AgentApp: https://flower.ai/docs/agent/tutorials/write-your-first-agentapp.html
- Run on SuperGrid: https://flower.ai/docs/agent/how-to-guides/run-on-supergrid.html
- Local SuperLink: https://flower.ai/docs/agent/how-to-guides/run-with-local-superlink.html
- Connectors: https://flower.ai/docs/agent/explanations/use-connectors.html
- AgentApp runtime (`agent.grid`, run series, **do not mix AgentApp + ServerApp/ClientApp**): https://flower.ai/docs/agent/explanations/agentapp-runtime.html
- Publish to Flower Hub: https://flower.ai/docs/agent/how-to-guides/use-flower-hub.html#publish-your-agentapp
- Hub publish (framework): https://flower.ai/docs/hub/how-to-publish-app-on-hub.html
- Federations on SuperGrid: https://flower.ai/docs/framework/how-to-create-and-manage-federations.html
- Architecture (SuperLink/SuperNode): https://flower.ai/docs/framework/explanation-flower-architecture.html
- SuperGrid announce blog: https://flower.ai/blog/2025-09-25-flower-supergrid
- Endeavor model (bonus): https://flower.ai/models/endeavor

**Templates / Hub / sample repo (Grid / collaborative)**
- Hub AgentApp template: https://flower.ai/apps/flwrlabs/agent → `flwr new @flwrlabs/agent`
- Hub Collaborative AgentApp: https://flower.ai/apps/flwrlabs/collaborative-agent → `flwr new @flwrlabs/collaborative-agent`
- Hackathon collab recipe (Hub): https://flower.ai/apps/flwrlabs/hackathon-collab-agent-recipe → `flwr new @flwrlabs/hackathon-collab-agent-recipe`
- Discuss-linked GitHub (Grid tools across SuperNodes): https://github.com/jafermarq/flower-collaborative-agent-hackathon
- AgentGrid API: https://flower.ai/docs/framework/ref-api/flwr.agentapp.AgentGrid.html

**CLI reminders:** `flwr login supergrid` · `flwr chat` · `flwr run . supergrid --stream` · `flwr app publish .` · `flwr list` / `flwr log <run-id> supergrid --show`

### 3. Sharpened P0 checklist (score-critical)

**MUST-DO (before ~17:15 PT demos)**
- [ ] **Grid tools visible:** Orchestrator (or collab AgentApp) uses `agent.grid` / Grid sample·message path between ≥2 roles (HospitalCred ↔ PayerEnrollment) — not a single chat wrapper
- [ ] **SuperGrid UI or Flower Chat** shows the live run / handoff (screenshot + live)
- [ ] **HITL** hard gate: Approve / Escalate / Reject required before claim receipt
- [ ] **Synthetic fixtures only** — no live CAQH/NPDB/PHI
- [ ] **Flower Hub publish** of AgentApp (`flwr app publish .`) — URL in Typeform
- [ ] **Typeform** https://flowerlabs.typeform.com/to/rQuplUGG — team name, members, emails, short description, Hub app, GitHub
- [ ] **GitHub** public repo link on form
- [ ] Spoken order: **Flower/SuperGrid first** → problem → working result (official demo guidance)
- [ ] Recorded fallback ready if SuperGrid/credits flake

**NICE-TO-HAVE**
- [ ] **Endeavor** on ≥1 agent (see §4) — say it once aloud
- [ ] Run-event / claim panel screenshotable (Franco)
- [ ] ≤45s “why not just Symplr?” beat (centralize vs federated claims)
- [ ] Nebius SuperNode only if mentors make multi-node trivially online

**DO-NOT**
- [ ] Single AgentApp that never samples/messages another agent/node
- [ ] Mix ServerApp/ClientApp vertical-FL math into the same FAB as AgentApp
- [ ] Steal Symplr “75%” / “9/10” / HITRUST-of-us
- [ ] Live scrapers or “HIPAA-certified product” claims

### 4. Endeavor bonus without derailing the demo

Official wording: *“Bonus points if you use our recently released Endeavor model.”* (discuss) · product: https://flower.ai/models/endeavor

**How (minimal risk):**
1. Set **one** agent’s model to Endeavor via SuperGrid/Flower AI model config (OpenRouter-style name from mentors/Slack if needed — **confirm exact model id in `#hackathon_stanford_2026`**; do not invent an id on stage).
2. Prefer Endeavor on the **orchestrator** (reasoning over claim aggregation) OR the HITL-assist copy — not on every node.
3. In demo: one sentence — “Orchestrator reasoning is on Endeavor” — then continue to HITL/receipt. **Do not** spend time on model bake-offs.
4. If Endeavor endpoint is flaky: fall back to whatever Nebius/Flower model is live; keep Grid handoff + HITL (primary criteria > bonus).

**Uncertainty:** Exact `openai/...` / Flower model string for Endeavor on SuperGrid today may be Slack-day-of — verify before dry-run; do not hard-fail the demo on Endeavor.

### 5. Submit gates checklist (easy to miss)

From discuss “Submission and demos”:
1. Typeform team details (name, members, emails) — https://flowerlabs.typeform.com/to/rQuplUGG
2. **Published** Flower Hub AgentApp (not just local FAB)
3. Short project description (on form)
4. GitHub repository link
5. 3–5 min live demo starting **17:15 PT**; dinner 18:00; awards 18:45
6. Operational limits: SuperGrid task **5-minute timeout** from Running; ask mentors for credits if needed

### 6. Lift lines for Pablo / Sofia / Leo

- One-liner: “Credentialing is distributed verification pretending to be paperwork — Flower Agents on SuperGrid make the distribution explicit, private, and human-supervised.”
- Flower score: “Judges will see SuperGrid multi-agent handoff, Grid tools between hospital and payer roles, and a human approval gate — not a CAQH clone.”
- Impact: “Payer leaders buy centralized PDM/CVO stacks like Symplr; we demo federated verification claims so attributes never leave the node.”
- Honesty footer: “Synthetic fixtures only — no live PHI, NPDB, or CAQH scrape.”


### Typeform URL note
Correct team form: https://flowerlabs.typeform.com/to/rQuplUGG (lowercase **l** before UGG). A capital-I variant (`rQupIUGG`) resolves to a generic Typeform marketing page — do not use.
