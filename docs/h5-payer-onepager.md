# H5 — RushPoppy one-pager for payer leaders (FLOWER-21)

**Audience:** Network Management · Credentialing / CVO ops · Executive / payer operations leaders  
**Competitive context (fair cite only):** https://www.symplr.com/solutions/payer-leaders  
**When:** Post-demo / Impact & sales after ~17:15 PT — **not** MVP Build scored work  
**Banned:** HITRUST-as-ours · HIPAA-certified · “75% faster” / inventing Symplr % · live CAQH/NPDB promises

---

## Problem

Payer leaders inherit **siloed, centralized provider-data friction**: dossiers and golden records concentrate risk and delay enrollment decisions, while privacy and primary-source constraints push teams toward heavyweight CVO-style stacks. Buyers already know that category (Symplr payer-leaders and peers). What’s missing is a path where **distribution and human governance are explicit** — not another promise that everything must land in one vault first.

## Solution (RushPoppy on Flower)

**Federated verification claims on Flower SuperGrid**, gated by humans:

1. **HospitalCred SuperNode** and **PayerEnrollment SuperNode** keep attributes local.
2. Nodes exchange **typed claims** (MVP: `license_active`, `npi_enumerated`, `exclusion_clear`, `work_history_complete`).
3. **PoppyOrchestrator** aggregates claim results over the Collaborative AgentApp Grid.
4. **HITL panel** — Approve / Escalate / Reject — never auto-approve.
5. **Auditable receipt** emits only after Approve (F8).

One-liner: *Attributes stay local. Claims move. A human gates the outcome.*

## Who it’s for (ICP)

| Role (Symplr payer-page framing) | Why they care |
|----------------------------------|---------------|
| Network Management | Enrollment / participation decisions without full dossier dump |
| Credentialing / CVO ops | Typed PSV-style claims + HITL instead of opaque batch |
| Executive / payer ops | Explicit governance trail (receipt) without claiming a GRC suite |

## MVP vs roadmap

| Now (hackathon MVP) | Later (post-demo backlog) |
|---------------------|---------------------------|
| Synthetic fixtures only | Broader enrollment claim types (H4a) |
| 2 SuperNode scaffolds + local FakeAgentGrid | Multi-payer federation N×M (H4b) |
| HITL panel + claim receipt | Audit-export packet from run-series (H4c) |
| Local E2E dry-run | Directory-lite member steering — **explicitly later**; we do **not** replace Symplr Directory (H4d) |
| Endeavor optional for narrative | Security/compliance roadmap toward enterprise assurances **without** HITRUST-as-ours today (H4e) |

## Competitive honesty

- Symplr = **category example** of centralized PDM / CVO / Directory / compliance — not a strawman, not a clone target for MVP.
- We do **not** claim Symplr’s marketing percentages as facts or as ours.
- We do **not** claim HITRUST, HIPAA certification, or live CAQH/NPDB for RushPoppy in this demo.

## Ask

Pilot a **synthetic federated-claims** path with your network + credentialing leads: two SuperNodes, HITL gate, screenshotable receipt. Expand claim types and federation after the hackathon — see `docs/backlog/`.

---

*Source tree:* `docs/h1-competitive-tear-sheet.md` · `docs/h2-why-not-symplr-beat.md` · `docs/h3-symplr-callout.md` · `docs/backlog/`
