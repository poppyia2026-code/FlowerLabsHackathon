# Real Flower runtime — F4 / G2

This path uses Flower 1.39, real Grid replies, and human review in Flower Chat.
A local unit-test result is **not** evidence of a live SuperGrid deployment.

## What changed

- The coordinator consumes the two SuperNodes' replies instead of re-reading
  local fixture files after a cosmetic Grid handoff.
- Pending, malformed, misidentified, or missing replies fail closed. There is
  no fallback that manufactures a successful reply from a local fixture.
- Flower runs the same FAB on the coordinator and the workers. Each worker
  dispatches using its locally configured `poppy-role`, reads `agent.prompt`
  (Flower's instruction envelope), and uses `push_reply_message` once.
- Each worker requires its own `poppy-data` path. Data fixtures are excluded
  from the FAB; the coordinator needs no copy of either shard.
- Flower Chat saves a pending review in a `ConfigRecord`. The next human chat
  command approves, escalates or rejects that exact review. Automatic approval
  is disabled. Expired reviews and repeated decision commands cannot approve.

## Repeat the real local integration test

```sh
uv sync --extra dev
uv run python scripts/smoke_local_flower.py
```

On macOS/Linux this starts one real SuperLink and two real SuperNodes with TLS
and distinct authentication keys on loopback ports. It verifies actual replies,
review state across chat turns, approve/escalate/reject, invalid review IDs,
replay protection, and a node going offline. It stops all processes afterward;
ignored `.flwr-local/smoke-*/` directories retain logs and run-event JSON.

The script deliberately sends automated **test** decisions for synthetic
providers. It does not represent a real human review. It uses the installed
Flower 1.39 environment and disables runtime dependency installation only in
these temporary local processes. No cloud registration or account is used.

## Prepare the demo machine

```sh
uv sync --extra dev
uv run python -m pytest -q
uv run flwr build
uv run flwr login supergrid
```

Use the team's existing authorized deployment federation. Confirm its name with
`uv run flwr federation list supergrid` before registering anything. Registration
adds these demo machines to that account; it does not publish the app.

If equivalent nodes already exist, reuse their authorized keys instead of
creating duplicate registrations. Otherwise generate distinct keys locally:

```sh
mkdir -p keys
ssh-keygen -t ecdsa -b 384 -N '' -f keys/hospital-cred
ssh-keygen -t ecdsa -b 384 -N '' -f keys/payer-enrollment
uv run flwr supernode register keys/hospital-cred.pub supergrid --name HospitalCred
uv run flwr supernode register keys/payer-enrollment.pub supergrid --name PayerEnrollment
```

Add those two returned IDs to the team's deployment federation in Flower or
with `flwr federation add-supernode <NODE_ID> @account/federation supergrid`.
Only public keys are registered. Keep private keys and `.env` files out of Git.

## Start one process per institution

On the hospital machine, copy only its synthetic shard to a local data folder;
on the payer machine, copy only the payer shard. For a laptop demonstration,
two processes can represent the institutions, but that is not physical isolation.

```sh
uv run python scripts/run_supernode.py HospitalCred \
  --data fixtures/supernodes/HospitalCred/providers.json \
  --key keys/hospital-cred --port 8011
```

In a separate terminal:

```sh
uv run python scripts/run_supernode.py PayerEnrollment \
  --data fixtures/supernodes/PayerEnrollment/providers.json \
  --key keys/payer-enrollment --port 8012
```

### Docker alternative (no local Flower install)

`compose.yaml` starts both nodes from the official `flwr/supernode:1.39.0`
image with the same `poppy-role` / `poppy-data` node config. Each container
mounts only its own shard, read-only. It expects `keys/supernode-0`
(HospitalCred) and `keys/supernode-1` (PayerEnrollment):

```sh
export FLWR_MODEL_API_KEY="..."   # flower.ai -> Profile -> Settings -> API Keys
docker compose up
```

Both names must be unique and exactly match `HospitalCred` and `PayerEnrollment`.
Check `uv run flwr supernode list supergrid` and the federation membership before
launching the app. A successful registration alone does not prove the node is online.

## Review in Flower Chat

Select the local AgentApp and the deployment federation in `uv run flwr chat`,
or select the published AgentApp in the same federation in the browser.
In the CLI, use `/load .` from this checkout and `/federation @account/federation`
with the actual team federation. Keep the conversation open for the decision
turn; a separate `flwr run` invocation starts a new conversation.

1. Send `Verify SYNTH-NPI-1999999999 for SYNTH-NETWORK-X`.
2. Confirm two actual node responses and a **pending** review, without a receipt.
3. Read the claim values and send `/approve run-<ID shown in the response>`.
4. Check the synthetic receipt. Repeat with `/escalate` and `/reject` in new cases.
5. Test `SYNTH-NPI-1888888888` to see different evidence. The app must not silently
   switch back to the default provider.
6. In an authorized demo environment, stop one demo node and verify the missing
   response remains missing. An approval cannot produce a credentialed outcome.

The review is a synthetic credential-verification result, not payment or an
external insurer's acceptance. This change does not add CAQH, NPDB, EHR, or payer
integrations. Model assistance remains optional and must not make the human
review decision.

Record actual startup time, run IDs and outcomes for FLOWER-10/G2. Do not close
those tickets based on unit tests, a FAB build, or a local simulation alone.

## Sources

- Flower 1.39 AgentApp runtime: https://flower.ai/docs/agent/explanations/agentapp-runtime.html
- Chat output events: https://flower.ai/docs/agent/how-to-guides/use-openai-sdk.html#publish-agentapp-generated-text
- Organizer deployment example: https://github.com/jafermarq/flower-collaborative-agent-hackathon
