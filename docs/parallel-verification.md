# Concurrent institution verification

The first live round now discovers both institutions once, pushes their two
independent requests together, and waits for both replies in one Grid call.
The coordinator never shares its Grid client across threads. Each institution
still receives only its own claim types and reads its own local data file.

Replies are correlated by instruction message ID, then checked against source
node, request ID, provider ID, role and synthetic scope. Arrival order is not
significant. Missing, duplicate or invalid replies cannot produce a successful
verification; a valid response from the other institution remains reviewable.
An unresolved conflict still blocks approval. Follow-up questions are sent only
after the first round and consume the same remaining time budget.

## Local validation, 2026-09-29

- 211 tests, plus 9 subtests, passed.
- Real local Flower 1.39 smoke passed: TLS SuperLink, two authenticated
  SuperNodes, separate data, human-review state across turns, wrong IDs,
  replay protection, approvals, escalations, rejections, both conflict paths,
  node-specific wording through a local model stand-in, and an offline node.
- Actual Grid events show one two-message push and three tool calls for the
  initial collection. A conflict adds one single-message push and three calls.
- Organization fixtures remain excluded from the FAB.

The table compares main `59aeaee` with this change on the same Mac. These are
individual observations, not a statistical benchmark. Nodes were already
online; decisions were automated test commands on synthetic providers, and
the model provider was a local stand-in. The measured interval starts with
chat submission and ends with the completed review turn, before approval.

| Scenario | Sequential main | Concurrent, final validation |
| --- | ---: | ---: |
| Sources agree (provider P) | 9.089 s | 5.052 s |
| Conflict explained (provider R) | 15.145 s | 11.123 s |
| Conflict unresolved (provider S) | 15.624 s | 11.597 s |

An earlier concurrent validation measured 5.606 / 9.092 / 9.591 s for the same
three cases. Runtime scheduling varies; do not present these as a guaranteed
percentage improvement, a SuperGrid result or real credentialing time saved.

`scripts/smoke_local_flower.py` records per-turn timings in its ignored
`result.json`. Re-run on the actual demo federation before replacing a stable
published version. This change does not add or replace any model.
