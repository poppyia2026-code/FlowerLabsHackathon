# H4b — Multi-payer federation story (FLOWER-27)

**Parent:** FLOWER-22 · **not MVP**

## Narrative

Hackathon MVP shows **1 hospital SuperNode × 1 payer SuperNode**. Post-demo story: **N hospital SuperNodes × M payer SuperNodes** federate typed claims without centralizing dossiers.

```
HospitalCred_1 … HospitalCred_N
        \         /
         SuperGrid (claims)
        /         \
PayerEnrollment_1 … PayerEnrollment_M
              |
      PoppyOrchestrator + HITL
              |
         claim receipt(s)
```

## Acceptance criteria (backlog)

- [ ] Storyboard / sequence diagram for N×M claim fan-in
- [ ] Orchestrator policy: which claims required per payer
- [ ] Fail-soft when one payer node is down (extend G3)
- [ ] Explicit: attributes never leave owning SuperNode; only claims cross

## Out of scope

Building N×M on demo day · live payer integrations · inventing Symplr %
