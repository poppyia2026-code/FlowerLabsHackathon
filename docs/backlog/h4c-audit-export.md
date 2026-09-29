# H4c — Audit-export / compliance packet (FLOWER-26)

**Parent:** FLOWER-22 · **not MVP**  
**Compete with “compliance visibility,” not a full GRC suite.**

## Goal

Export a **run-series event packet** (kickoff → Grid claims → HITL decision → receipt) that payer compliance / ops can attach to an internal review — a visibility metaphor, **not** a GRC product claim.

## Packet contents (draft)

- Run id + timestamps
- SuperNode ids (hospital / payer) — no raw PHI attributes
- Claim type results (typed flags only)
- HITL actor + decision (Approve / Escalate / Reject)
- Receipt hash / id if Approve
- Explicit disclaimer: synthetic demo vs production data class

## Acceptance criteria (backlog)

- [ ] Export format (JSON + human PDF/Markdown) specified
- [ ] Non-GRC wording in UI/docs (“audit visibility packet”)
- [ ] Redaction rules: attributes stay on nodes; packet is claims+governance only
- [ ] No HITRUST / HIPAA-certified product claim attached to the export

## Out of scope

Full GRC suite · HITRUST-as-ours · live CAQH/NPDB evidence pulls
