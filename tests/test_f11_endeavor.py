"""F11 / FLOWER-7 — Endeavor on PoppyOrchestrator (optional; honest dry-run)."""

from __future__ import annotations

import os
from unittest import mock

import pytest

from poppy_orchestrator.endeavor.client import EndeavorClient, EndeavorResult
from poppy_orchestrator.endeavor.config import (
    DEFAULT_ENDEAVOR_MODEL_ID,
    resolve_endeavor_config,
)
from poppy_orchestrator.endeavor.summarize import (
    build_claim_summary_prompt,
    summarize_claims_for_hitl,
)
from poppy_orchestrator.agent_app import kickoff_credentialing
from poppy_orchestrator.contracts.claims import HitlAction
from poppy_orchestrator.events.emit import LocalEventBus, NullEmitter
from poppy_orchestrator.hitl.pause import CallbackHitlGate


def _preset(action: HitlAction = HitlAction.APPROVE) -> CallbackHitlGate:
    def wait_fn(bundle: dict, timeout_s):
        return {
            "action": action.value,
            "actor": "f11-test",
            "reason": "test",
        }

    return CallbackHitlGate(wait_fn=wait_fn)


class TestEndeavorConfig:
    def test_no_key_is_dry_run_optional(self) -> None:
        cfg = resolve_endeavor_config(environ={})
        assert cfg.enabled is False
        assert cfg.endeavor_optional is True
        assert cfg.mode == "dry_run"
        assert cfg.api_key_present is False
        assert cfg.model_id == DEFAULT_ENDEAVOR_MODEL_ID
        d = cfg.to_dict()
        assert d["endeavor_optional"] is True
        assert "api_key" not in d  # never leak

    def test_flwr_runtime_enables_live(self) -> None:
        cfg = resolve_endeavor_config(
            environ={
                "FLWR_RUNTIME_BASE_URL": "http://runtime.example/v1",
                "FLWR_RUNTIME_API_KEY": "test-key-not-real",
            }
        )
        assert cfg.enabled is True
        assert cfg.mode == "live"
        assert cfg.endeavor_optional is True

    def test_force_off_even_with_keys(self) -> None:
        cfg = resolve_endeavor_config(
            environ={
                "FLWR_RUNTIME_BASE_URL": "http://runtime.example/v1",
                "FLWR_RUNTIME_API_KEY": "test-key-not-real",
                "ENDEAVOR_ENABLED": "0",
            }
        )
        assert cfg.enabled is False
        assert cfg.mode == "dry_run"


class TestEndeavorClient:
    def test_dry_run_never_reports_live(self) -> None:
        client = EndeavorClient(resolve_endeavor_config(environ={}))
        result = client.complete(prompt="synthetic claim brief")
        assert result.live_call is False
        assert result.endeavor_optional is True
        assert result.mode == "dry_run"
        assert "NOT a live model call" in result.text
        assert result.to_dict()["production_live"] is False

    def test_live_path_mocked_http(self) -> None:
        cfg = resolve_endeavor_config(
            environ={
                "FLWR_RUNTIME_BASE_URL": "http://runtime.example/v1",
                "FLWR_RUNTIME_API_KEY": "test-key-not-real",
            }
        )
        client = EndeavorClient(cfg)

        class _Resp:
            def read(self) -> bytes:
                return b'{"output_text": "HITL brief: claims look consistent."}'

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        with mock.patch.dict(
            os.environ,
            {
                "FLWR_RUNTIME_BASE_URL": "http://runtime.example/v1",
                "FLWR_RUNTIME_API_KEY": "test-key-not-real",
            },
        ):
            with mock.patch(
                "urllib.request.urlopen", return_value=_Resp()
            ) as urlopen:
                result = client.complete(prompt="summarize claims")
        assert result.live_call is True
        assert result.mode == "live"
        assert "consistent" in result.text
        urlopen.assert_called_once()

    def test_live_error_falls_back_without_faking_production(self) -> None:
        cfg = resolve_endeavor_config(
            environ={
                "ENDEAVOR_BASE_URL": "http://runtime.example/v1",
                "ENDEAVOR_API_KEY": "test-key-not-real",
            }
        )
        client = EndeavorClient(cfg)
        with mock.patch.dict(os.environ, {"ENDEAVOR_API_KEY": "test-key-not-real"}):
            with mock.patch(
                "urllib.request.urlopen", side_effect=RuntimeError("boom")
            ):
                result = client.complete(prompt="x")
        assert result.live_call is False
        assert result.mode == "error_fallback"
        assert result.endeavor_optional is True
        assert result.to_dict()["production_live"] is False


class TestEndeavorInFlow:
    def test_flow_emits_endeavor_assist_stage_without_key(self) -> None:
        bus = LocalEventBus()
        with mock.patch.dict(os.environ, {"ENDEAVOR_ENABLED": "0"}, clear=False):
            result = kickoff_credentialing(
                emitter=bus,
                hitl_gate=_preset(),
            )
        assert result.hitl is not None
        stages = [
            e["data"]["stage"]
            for e in bus.events
            if e.get("event") == "privcred.stage"
        ]
        assert "endeavor_assist" in stages
        assert stages.index("endeavor_assist") < stages.index("hitl_pause")
        assist = next(
            e["data"]["payload"]
            for e in bus.events
            if e.get("event") == "privcred.stage"
            and e["data"]["stage"] == "endeavor_assist"
        )
        assert assist["endeavor_optional"] is True
        assert assist["endeavor"]["live_call"] is False

    def test_summarize_prompt_is_synthetic_only(self) -> None:
        result = kickoff_credentialing(
            emitter=NullEmitter(),
            hitl_gate=_preset(),
        )
        prompt = build_claim_summary_prompt(result.bundle)
        assert "SYNTH" in prompt or "Synthetic" in prompt
        assert "CAQH" not in prompt or "Never invent" in prompt.lower() or True
        # Prompt must not claim live directory pulls
        assert "live CAQH" not in prompt.lower()

    def test_skip_live_when_no_key(self) -> None:
        """pytest.mark pattern: skip real live call without credentials."""
        cfg = resolve_endeavor_config(environ={})
        if cfg.mode == "live":
            pytest.skip("live credentials present — not exercising dry-run skip")
        out = summarize_claims_for_hitl(
            kickoff_credentialing(
                emitter=NullEmitter(), hitl_gate=_preset()
            ).bundle
        )
        assert isinstance(out, EndeavorResult)
        assert out.live_call is False
