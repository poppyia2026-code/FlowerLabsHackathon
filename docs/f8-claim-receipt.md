# F8 — Auditable claim receipt after Approve (FLOWER-13)

Delivery beat for judges: after HITL **Approve**, emit a screenshotable
run-series receipt. **No receipt** on Escalate or Reject.

## Hook

`poppy_orchestrator.receipts.emit.emit_receipt_after_approve` — called from
`run_credentialing_flow` after `hitl_gate.wait_for_decision`.

| HITL | Receipt? | Outcome |
|------|----------|---------|
| Approve | **Yes** — `privcred.claim_receipt` + stage `claim_receipt` + text block | `credentialed` (or `failed` if node missing) |
| Escalate | No | `escalated` |
| Reject | No | `rejected` |

## Screenshotable artifacts

```bash
# Happy path → print text + JSON receipt
python scripts/print_receipt.py

# Fail-soft / deck examples
fixtures/receipts/example_approve.json
fixtures/receipts/example_approve.txt
```

Formats: `format_receipt_json` / `format_receipt_text` in
`poppy_orchestrator/receipts/format.py`.

## Constraints

- Synthetic demo only
- Do **not** claim HITRUST, HIPAA-certified audit packets, or compliance-suite product
- Never emit receipt without Approve
