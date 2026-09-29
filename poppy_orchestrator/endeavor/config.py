"""Endeavor config — optional bonus; never blocks Grid / HITL / Hub."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import os

# Default model id for Flower SuperGrid / AgentApp runtime.
# Confirm day-of in #hackathon_stanford_2026 if mentors publish a different string.
DEFAULT_ENDEAVOR_MODEL_ID = "flower/endeavor"

# Env names Flower injects inside a running AgentApp (see Flower Agent docs).
FLWR_RUNTIME_BASE_URL = "FLWR_RUNTIME_BASE_URL"
FLWR_RUNTIME_API_KEY = "FLWR_RUNTIME_API_KEY"

# Optional explicit overrides for local experiments (not required for dry-run).
ENDEAVOR_API_KEY = "ENDEAVOR_API_KEY"
ENDEAVOR_BASE_URL = "ENDEAVOR_BASE_URL"
ENDEAVOR_MODEL_ID = "ENDEAVOR_MODEL_ID"
# Master switch: set ENDEAVOR_ENABLED=0 to force dry-run even when keys exist.
ENDEAVOR_ENABLED = "ENDEAVOR_ENABLED"


@dataclass(frozen=True)
class EndeavorConfig:
    """Resolved Endeavor wiring for the Orchestrator role."""

    enabled: bool
    """False → dry-run stub path; never pretend a live model call happened."""

    endeavor_optional: bool
    """Always True for this MVP — Endeavor is a score bonus, never a hard dep."""

    model_id: str
    base_url: Optional[str]
    api_key_present: bool
    role: str = "PoppyOrchestrator"
    mode: str = "dry_run"  # dry_run | live
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "endeavor_optional": self.endeavor_optional,
            "model_id": self.model_id,
            "base_url_set": bool(self.base_url),
            "api_key_present": self.api_key_present,
            "role": self.role,
            "mode": self.mode,
            "reason": self.reason,
            # Never leak key material
            "synthetic_prompts_only": True,
        }


def resolve_endeavor_config(environ: Optional[dict] = None) -> EndeavorConfig:
    """Detect credentials honestly; default to dry-run when missing."""
    env = environ if environ is not None else os.environ
    model_id = (env.get(ENDEAVOR_MODEL_ID) or DEFAULT_ENDEAVOR_MODEL_ID).strip()
    force_off = str(env.get(ENDEAVOR_ENABLED, "1")).lower() in {"0", "false", "no", "off"}

    flwr_base = (env.get(FLWR_RUNTIME_BASE_URL) or "").strip() or None
    flwr_key = (env.get(FLWR_RUNTIME_API_KEY) or "").strip()
    explicit_base = (env.get(ENDEAVOR_BASE_URL) or "").strip() or None
    explicit_key = (env.get(ENDEAVOR_API_KEY) or "").strip()

    base_url = flwr_base or explicit_base
    key_present = bool(flwr_key or explicit_key)

    if force_off:
        return EndeavorConfig(
            enabled=False,
            endeavor_optional=True,
            model_id=model_id,
            base_url=base_url,
            api_key_present=key_present,
            mode="dry_run",
            reason="ENDEAVOR_ENABLED=0 — forced dry-run (Endeavor optional)",
        )

    if base_url and key_present:
        return EndeavorConfig(
            enabled=True,
            endeavor_optional=True,
            model_id=model_id,
            base_url=base_url,
            api_key_present=True,
            mode="live",
            reason="Flower runtime or ENDEAVOR_* credentials present",
        )

    return EndeavorConfig(
        enabled=False,
        endeavor_optional=True,
        model_id=model_id,
        base_url=base_url,
        api_key_present=key_present,
        mode="dry_run",
        reason=(
            "No API key in env (need FLWR_RUNTIME_* or ENDEAVOR_API_KEY) — "
            "Endeavor optional dry-run stub"
        ),
    )
