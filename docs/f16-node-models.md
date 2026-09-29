# F16 — Each organization brings its own model (FLOWER-36)

Synthetic only. No live CAQH / NPDB / PHI.

## What it shows

Three roles, up to three different models from different providers, in one
run. Nobody has to agree on a vendor to collaborate.

| Role | Runs on | Model and provider come from |
| --- | --- | --- |
| PoppyOrchestrator | SuperGrid | `endeavor-model-id` in `pyproject.toml`, Flower's runtime |
| HospitalCred | that organization's SuperNode | its own `poppy-model` and `FLWR_MODEL_API_*` |
| PayerEnrollment | that organization's SuperNode | its own `poppy-model` and `FLWR_MODEL_API_*` |

In the review, each worded line names the model that wrote it:

```text
- HospitalCred, asked again: True. <sentence> _(worded by dedicated/flowerai/MiniMax-M3-OOLI9o)_
```

## What the model does, and what it does not

A node's model rewrites one sentence a person will read: the note on a
follow-up answer, or the reason on a dispute.

- It is handed only the text that was already cleared to leave the node. It
  never sees the record, the evidence reference or any other field.
- It never produces an answer. `value`, `resolves_dispute` and `observed` come
  from the node's rules, before the model is called.
- A rewrite is dropped, and the fixed text sent, when the model fails, times
  out (15 s), returns nothing, returns more than 240 characters, or changes or
  drops any date or number.
- A node with no `poppy-model` makes no model call at all.

## Settings

Per SuperNode, in `--node-config`:

| Key | Meaning |
| --- | --- |
| `poppy-role` | `HospitalCred` or `PayerEnrollment` |
| `poppy-data` | path to that node's own data file |
| `poppy-model` | optional. Model id for this node |

Per SuperNode, in its environment:

| Provider | Variables |
| --- | --- |
| Flower AI | `FLWR_MODEL_API_KEY` |
| Nebius Token Factory | `FLWR_MODEL_API_KEY` and `FLWR_MODEL_API_ENDPOINT=https://api.tokenfactory.tf-ca1.nebius.com/v1/responses` |

Model ids on Nebius, from the hackathon guidelines:

- `dedicated/flowerai/Kimi-K2.7-Code-1OUHWL`
- `dedicated/flowerai/MiniMax-M3-OOLI9o`

Flower AI ids follow the OpenRouter format, for example `openai/gpt-5.6-sol`.
The id for Endeavor is **not confirmed**: `flower/endeavor` in
`pyproject.toml` is a guess and no public page lists it. Ask in
`#hackathon_stanford_2026` before the demo. With a wrong id the Orchestrator
falls back to its dry-run text and says so in the chat.

`ENDEAVOR_ENABLED=0` in a process's environment switches off every model call
in that process, node wording included.

## Start the nodes

With Docker, from the repository root:

```shell
export NEBIUS_API_KEY=...        # from the hackathon Slack
export FLOWER_API_KEY=...        # flower.ai, Profile, Settings, API Keys
export HOSPITAL_MODEL=dedicated/flowerai/MiniMax-M3-OOLI9o
export PAYER_MODEL=openai/gpt-5.6-sol
docker compose up
```

Without Docker:

```shell
python scripts/run_supernode.py HospitalCred \
  --data fixtures/supernodes/HospitalCred/providers.json \
  --key keys/supernode-hospital --model "$HOSPITAL_MODEL"
```

## Verification

- `pytest`: `tests/test_node_models.py`, `tests/test_import_order.py`
- `python scripts/smoke_local_flower.py`: passed on 2026-09-29 with a real
  local TLS SuperLink and two authenticated SuperNodes (Flower 1.39.0,
  Windows 11). HospitalCred was given its own provider endpoint; the run
  checks that its model calls reached that provider, that the reply named the
  model, that the typed answer did not change, that the provider received
  nothing but the note, and that PayerEnrollment, with no model, made no call.
  The provider in that run is a local stand-in, not Nebius.
- The conflict run took about 24 s with the model call included.

Not verified:

- A call to Nebius Token Factory or to Flower AI. No keys were available.
- What a real model returns. A rewrite that fails the checks above is dropped.
- `compose.yaml`. No Docker on the machine that wrote it.
- Any run on SuperGrid.
