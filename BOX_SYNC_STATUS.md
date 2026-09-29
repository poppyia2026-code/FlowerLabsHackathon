# Box sync status (2026-09-29 PT)

Complete verified scaffold lives here on Luigi's Mac:

`/Users/luigi.siano/Desktop/privcred-orchestrator/`

Also tarball: `/Users/luigi.siano/Desktop/privcred-orchestrator.tgz`

Dry-run verified:
- happy path → outcome `credentialed` + claim receipt
- escalate path (`SYNTH-NPI-1888888888`) → outcome `escalated`, no receipt

**Box `/workspace/privcred-orchestrator/` was partially written earlier, then box Shell/CopyToBox failed (HTTP 404 / spawn errors).** Parent/CoS should rsync this Desktop tree into `/workspace/privcred-orchestrator/` once box FS recovers.

Local HTTP mirror (if still up): `http://127.0.0.1:18765/`

Synced to box /workspace/privcred-orchestrator/ from Desktop tgz 2026-09-29.
