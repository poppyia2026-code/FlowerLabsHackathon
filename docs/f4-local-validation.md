# Flower 1.39 local validation — 2026-09-29

Validated on macOS with Python 3.13.14 and Flower 1.39.0.

- `python -m pytest -q`: **98 passed**, including 9 subtests.
- `flwr build`: succeeds; FAB inspection confirms no `fixtures/` files.
- `python scripts/smoke_local_flower.py`: **PASS** with real Flower processes.

The integration script started one TLS SuperLink and two authenticated
SuperNodes. Both nodes were online in **2.19 seconds** in this already-installed
local environment. This timing excludes dependency installation and is not a
measurement of SuperGrid startup.

The script submitted synthetic test decisions through the same Control API and
run-series mechanism used by Flower Chat. No real human or clinical decision
is represented by this test.

| Check | Actual local run | Observed result |
| --- | --- | --- |
| Collect both nodes | `13542669374931138122` | Six claims; pending review; no receipt |
| Wrong review ID | `5972286769951035720` | No decision or receipt |
| Explicit test approval | `10427585795419373084` | One receipt for the original reviewed bundle |
| Repeat approval | `16100201940679975907` | No additional receipt |
| Alternative provider | `7344182145415489712` | Correct provider; incomplete work history |
| Escalate | `6194709611333925365` | Escalated; no receipt |
| Alternative provider | `7796534036844086687` | Correct provider; incomplete work history |
| Reject | `6775716177602410543` | Rejected; no receipt |
| Stop PayerEnrollment | `10870759185064469996` | Missing payer remains missing |
| Approve with missing payer | `12104328186877640089` | Failed outcome; no credentialed receipt |

Re-run the script to produce new run IDs and full event JSON in
`.flwr-local/smoke-*/`. The script shuts down its own processes afterward.

## Still requires team deployment evidence

This validates local transport, worker dispatch, and persistent review state.
It does **not** verify deployment to SuperGrid, Flower Hub publication, or the
standalone F7 web panel. The institutions are represented by processes on one
laptop, not separate machines with enforced filesystem isolation. Data and
credentials are synthetic; no CAQH, NPDB, EHR, or payer system is integrated.

Keep F4/G2/F10 open until the team records the corresponding cloud run,
human-operated review, and publication evidence.
