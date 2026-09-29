# H3 — Symplr competitor callout (slide + landing) (FLOWER-24)

**Status:** CoS-ready copy · **non-blocking** for ~17:15 PT demo  
**Cite (fair use):** https://www.symplr.com/solutions/payer-leaders  
**Landing:** separate repo (`privcred-landing`) — paste from **Landing snippet** below; this file is source of truth in FlowerLabsHackathon.

**Banned:** HITRUST-as-ours · HIPAA-certified · inventing Symplr % (“75% faster”, “9/10”) · “we replace Symplr Directory today” · live CAQH/NPDB

## Slide callout (1 panel)

**Headline:** Incumbents centralize. We make distribution explicit on Flower.

**Body (≤40 words):**
Payer leaders already buy centralized provider-data / CVO-style stacks (e.g. Symplr’s payer-leaders suite). RushPoppy’s wedge is different: hospital and payer SuperNodes keep attributes local and exchange **typed verification claims** on Flower SuperGrid — with a human gate before any receipt.

**Footer line:** Fair-use category example → symplr.com/solutions/payer-leaders · Synthetic claims only · HITL required

## Landing snippet (optional paste into privcred-landing)

```html
<section id="competitor-callout" aria-label="Category context">
  <h2>Incumbents centralize. We make distribution explicit on Flower.</h2>
  <p>
    Network, credentialing, and executive leaders already evaluate centralized
    payer operations platforms — for example
    <a href="https://www.symplr.com/solutions/payer-leaders" rel="noopener noreferrer">
      Symplr’s solutions for payer leaders
    </a>
    (PDM, CVO-style PSV, directory, compliance). RushPoppy is not that suite.
  </p>
  <p>
    On Flower SuperGrid, a hospital SuperNode and a payer SuperNode exchange
    <strong>federated verification claims</strong>. PoppyOrchestrator aggregates
    them; a human Approves, Escalates, or Rejects; only then we emit an auditable
    receipt. Attributes stay local. Governance stays explicit.
  </p>
  <p class="fine-print">
    Hackathon MVP uses synthetic fixtures only — no live CAQH/NPDB, no PHI pulls,
    and no HITRUST or HIPAA-certified product claim for RushPoppy.
  </p>
</section>
```

## Markdown-only landing block (if HTML not used)

> **Incumbents centralize. We make distribution explicit on Flower.**  
> Category example: [Symplr — solutions for payer leaders](https://www.symplr.com/solutions/payer-leaders).  
> RushPoppy: federated claims on SuperGrid + HITL gate + auditable receipt. Synthetic MVP only. Not a Directory replacement. Not HITRUST/HIPAA-certified as ours.

## Placement notes

| Surface | Action |
|---------|--------|
| Pitch slide (Sofia) | One callout panel; **cut freely** if blocking demo time |
| Landing (Leo) | Optional section; copy lives here until pasted into `privcred-landing` |
| Demo script | Prefer H2 beat (`docs/h2-why-not-symplr-beat.md`) if only one Symplr mention fits |

## Done when (this ticket)

- [x] Slide + landing callout text exists in-repo
- [x] Fair-use Symplr link present
- [x] Explicitly non-blocking for demo time
