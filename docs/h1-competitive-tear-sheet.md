# H1 — Competitive tear-sheet for payer ICP (FLOWER-17)

**Cite only:** https://www.symplr.com/solutions/payer-leaders  
**Fair use:** Symplr as category example of centralized payer provider-data / CVO-style stacks.  
**Not ours:** no HITRUST-as-ours, no HIPAA-certified product claim, no “75% faster,” no “9/10 plans,” no live CAQH.

## ICP roles (from Symplr payer-leaders page framing)

- Network Management leaders
- Credentialing / CVO operations leaders
- Executive / payer operations leaders

## Module map → RushPoppy federated-claims wedge

| Symplr-class module (category) | What buyers hear today | RushPoppy MVP wedge on Flower |
|--------------------------------|------------------------|--------------------------------|
| Provider Data Management (PDM) | Centralized dossier / golden record | Attributes stay on SuperNodes; **claims** move |
| CVO / PSV | Primary-source verification as a service | Synthetic typed claims (`license_active`, `npi_enumerated`, `exclusion_clear`, `work_history_complete`) — **no live CAQH/NPDB in MVP** |
| Directory | Member / provider directory products | **Explicitly later** (H4d) — we do **not** replace Symplr Directory today |
| Compliance / audit visibility | Enterprise compliance tooling | Auditable **claim receipt** after HITL Approve (F8) — visibility metaphor, not a GRC suite |
| Network participation / enrollment | Payer network ops | PayerEnrollment SuperNode claim slice (disjoint from HospitalCred) |

## One-liner for Impact beat

“Payer leaders already buy centralized PDM and CVO-style stacks. RushPoppy makes distribution explicit on Flower SuperGrid: hospital and payer SuperNodes exchange verification claims; a human gates the outcome.”

## Honesty footer (always)

- Synthetic fixtures only in this hackathon demo
- No live PHI / CAQH / NPDB pulls
- Not claiming HITRUST or HIPAA certification for RushPoppy
- Not stealing Symplr marketing percentages as ours or as independent fact
