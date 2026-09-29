# F12 — Conflicting claims (FLOWER-33)

Synthetic only. No live CAQH / NPDB / PHI.

## What it shows

Two organizations disagree about one provider. The Orchestrator goes back to
the organization that owns the claim, once, with the exact period in question.
A person then decides with both answers in front of them.

| Provider | What happens | What the reviewer can do |
| --- | --- | --- |
| `SYNTH-NPI-1999999999` (P) | Sources agree. No second round. | approve, escalate, reject |
| `SYNTH-NPI-1777777777` (R) | Payer sees a 7-month gap. Hospital, asked again, has documented leave for it. Status `explained`. | approve, escalate, reject |
| `SYNTH-NPI-1666666666` (S) | Same gap. Hospital, asked again, has no record. Status `unresolved`. | escalate, reject |

## Rules

- A node never answers a claim it does not own. PayerEnrollment does not
  return `work_history_complete`; it raises a dispute against it.
- The Orchestrator re-asks the owner once per disputed claim. There is no
  third round.
- Status comes from the owner's second answer:
  - `agreed`: the owner now reports what the other node saw
  - `explained`: the owner keeps its answer and its records account for the period
  - `unresolved`: anything else, including no usable answer
- An unresolved conflict cannot be approved. `/approve` applies nothing and
  the review stays pending. Offline paths map it to `failed`.
- A receipt issued after a dispute records it in `message`.

## Messages on the Grid

| Round | To | Carries |
| --- | --- | --- |
| 1 | HospitalCred | its own claim types |
| 1 | PayerEnrollment | its own claim types; the reply may include `disputes` |
| 2 | HospitalCred | the one disputed claim type and `recheck` (claim, what was seen, period, reason) |

Round 2 sends the hospital only what the payer objected to, never the
payer's records.

## Demo script

In Flower Chat:

```text
Verify SYNTH-NPI-1777777777 for SYNTH-NETWORK-X
/approve run-<id>
```

```text
Verify SYNTH-NPI-1666666666 for SYNTH-NETWORK-X
/approve run-<id>          (refused, review stays pending)
/escalate run-<id> seven month gap
```

## Before running on SuperNodes

Fixture data is not inside the FAB. Each SuperNode reads the file named in its
own `poppy-data` setting, so the two new providers only exist on a node after
its file is updated:

- HospitalCred: `fixtures/supernodes/HospitalCred/providers.json`
- PayerEnrollment: `fixtures/supernodes/PayerEnrollment/providers.json`

A node with the old file answers `unknown synthetic provider` and the run
fails closed.

## Verification

- `pytest`: `tests/test_conflicting_claims.py`, `tests/test_conflict_contract.py`
- Not run against real Flower processes or SuperGrid.
