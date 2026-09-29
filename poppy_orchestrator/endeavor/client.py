"""Endeavor client — live OpenAI-compatible call OR honest dry-run stub."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
import json
import urllib.error
import urllib.request

from poppy_orchestrator.endeavor.config import EndeavorConfig, resolve_endeavor_config


@dataclass
class EndeavorResult:
    """Outcome of an Endeavor invoke — always tagged with mode + optional flag."""

    text: str
    mode: str  # dry_run | live | error_fallback
    endeavor_optional: bool
    model_id: str
    role: str
    live_call: bool
    error: Optional[str] = None
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "mode": self.mode,
            "endeavor_optional": self.endeavor_optional,
            "model_id": self.model_id,
            "role": self.role,
            "live_call": self.live_call,
            "error": self.error,
            "meta": self.meta,
            # Explicit honesty: dry-run is never production
            "production_live": self.live_call and self.mode == "live",
        }


class EndeavorClient:
    """Thin wrapper around Flower's OpenAI-compatible Responses endpoint.

    Without credentials → dry-run stub (endeavor_optional=True).
    Never reports dry-run output as a live production model call.
    """

    def __init__(self, config: Optional[EndeavorConfig] = None) -> None:
        self.config = config or resolve_endeavor_config()

    def complete(
        self,
        *,
        prompt: str,
        instructions: str = "",
        timeout_s: float = 20.0,
    ) -> EndeavorResult:
        cfg = self.config
        if not cfg.enabled or cfg.mode != "live":
            return self._dry_run(prompt, reason=cfg.reason)

        try:
            text = self._live_responses_create(
                prompt=prompt,
                instructions=instructions,
                timeout_s=timeout_s,
            )
            return EndeavorResult(
                text=text,
                mode="live",
                endeavor_optional=True,
                model_id=cfg.model_id,
                role=cfg.role,
                live_call=True,
                meta={"instructions_set": bool(instructions)},
            )
        except Exception as exc:  # noqa: BLE001 — bonus path must never crash flow
            stub = self._dry_run(
                prompt,
                reason=f"live call failed ({type(exc).__name__}); falling back to stub",
            )
            stub.mode = "error_fallback"
            stub.error = str(exc)[:240]
            stub.live_call = False
            return stub

    def _dry_run(self, prompt: str, *, reason: str) -> EndeavorResult:
        cfg = self.config
        preview = prompt.strip().replace("\n", " ")[:160]
        text = (
            "[ENDEAVOR DRY-RUN — endeavor_optional=true — NOT a live model call] "
            f"Orchestrator would reason over: {preview}…"
            if preview
            else (
                "[ENDEAVOR DRY-RUN — endeavor_optional=true — NOT a live model call] "
                "No prompt provided."
            )
        )
        return EndeavorResult(
            text=text,
            mode="dry_run",
            endeavor_optional=True,
            model_id=cfg.model_id,
            role=cfg.role,
            live_call=False,
            meta={"reason": reason, "production_live": False},
        )

    def _live_responses_create(
        self,
        *,
        prompt: str,
        instructions: str,
        timeout_s: float,
    ) -> str:
        """POST /responses (OpenAI-compatible) using urllib — no openai dep required."""
        import os

        cfg = self.config
        assert cfg.base_url, "live mode requires base_url"
        api_key = (
            os.environ.get("FLWR_RUNTIME_API_KEY")
            or os.environ.get("ENDEAVOR_API_KEY")
            or ""
        )
        if not api_key:
            raise RuntimeError("API key missing at live call time")

        url = cfg.base_url.rstrip("/") + "/responses"
        body: dict[str, Any] = {
            "model": cfg.model_id,
            "input": prompt,
        }
        if instructions:
            body["instructions"] = instructions

        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:  # noqa: S310
            payload = json.loads(resp.read().decode("utf-8"))
        return _extract_response_text(payload)


def _extract_response_text(payload: dict[str, Any]) -> str:
    """Best-effort extract from OpenAI Responses API shapes."""
    if isinstance(payload.get("output_text"), str) and payload["output_text"].strip():
        return payload["output_text"].strip()
    output = payload.get("output")
    if isinstance(output, list):
        chunks: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") in {
                        "output_text",
                        "text",
                    }:
                        t = part.get("text")
                        if isinstance(t, str):
                            chunks.append(t)
            elif isinstance(item.get("text"), str):
                chunks.append(item["text"])
        if chunks:
            return "\n".join(chunks).strip()
    # Chat-completions-ish fallback
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        msg = choices[0].get("message") if isinstance(choices[0], dict) else None
        if isinstance(msg, dict) and isinstance(msg.get("content"), str):
            return msg["content"].strip()
    raise ValueError("Could not extract text from Endeavor response payload")
