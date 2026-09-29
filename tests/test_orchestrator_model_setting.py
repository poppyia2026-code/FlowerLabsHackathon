"""`endeavor-model-id` in the run config is the model the Orchestrator asks for."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from poppy_orchestrator.endeavor.config import DEFAULT_ENDEAVOR_MODEL_ID
from poppy_orchestrator.orchestration.flow import OrchestratorConfig
from tests.test_same_fab_round_trip import Chat, Federation

pytest.importorskip("flwr.app")

ROOT = Path(__file__).resolve().parents[1]
HAPPY = "SYNTH-NPI-1999999999"


def asked_model(chat: Chat) -> str:
    for event in chat.events.items:
        data = event.get("data") or {}
        if data.get("stage") == "endeavor_assist":
            return data["payload"]["endeavor"]["model_id"]
    raise AssertionError("the Orchestrator never asked for a brief")


def test_run_config_chooses_the_model() -> None:
    chat = Chat(Federation())
    chat.context.run_config["endeavor-model-id"] = "openai/gpt-5.6-sol"

    chat.send(f"Verify {HAPPY} for SYNTH-NETWORK-X")

    assert asked_model(chat) == "openai/gpt-5.6-sol"


def test_run_config_wins_over_the_environment(monkeypatch) -> None:
    monkeypatch.setenv("ENDEAVOR_MODEL_ID", "from/environment")

    config = OrchestratorConfig(model_id="from/run-config").model_config()

    assert config is not None
    assert config.model_id == "from/run-config"


@pytest.mark.parametrize("missing", [None, ""])
def test_without_the_setting_the_default_is_used(missing) -> None:
    chat = Chat(Federation())
    if missing is not None:
        chat.context.run_config["endeavor-model-id"] = missing

    chat.send(f"Verify {HAPPY} for SYNTH-NETWORK-X")

    assert asked_model(chat) == DEFAULT_ENDEAVOR_MODEL_ID


def test_published_default_is_the_setting_the_code_reads() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert "endeavor-model-id" in config["tool"]["flwr"]["app"]["config"]
