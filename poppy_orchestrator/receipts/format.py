"""Screenshotable receipt formats for deck / G3 fail-soft kit (F8)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional, Union
import json
from datetime import datetime, timezone

from poppy_orchestrator.contracts.claims import ClaimReceipt


def _issued_iso(issued_at: float) -> str:
    return datetime.fromtimestamp(issued_at, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def format_receipt_json(receipt: Union[ClaimReceipt, Mapping[str, Any]], *, indent: int = 2) -> str:
    """Pretty JSON — screenshot / copy into deck slide."""
    data = receipt.to_dict() if isinstance(receipt, ClaimReceipt) else dict(receipt)
    return json.dumps(data, indent=indent, sort_keys=False) + "\n"


def format_receipt_text(receipt: Union[ClaimReceipt, Mapping[str, Any]]) -> str:
    """Human-readable receipt block for Flower Chat / fail-soft screenshot."""
    data = receipt.to_dict() if isinstance(receipt, ClaimReceipt) else dict(receipt)
    provider = data.get("provider") or {}
    hitl = data.get("hitl") or {}
    claims = data.get("claims_snapshot") or []
    run_series = data.get("run_series") or []
    issued = data.get("issued_at")
    issued_s = _issued_iso(float(issued)) if isinstance(issued, (int, float)) else str(issued)

    lines = [
        "╔══════════════════════════════════════════════════════════╗",
        "║  PrivCred — AUDITABLE CLAIM RECEIPT (synthetic MVP)     ║",
        "╚══════════════════════════════════════════════════════════╝",
        f"  receipt_id : {data.get('receipt_id')}",
        f"  run_id     : {data.get('run_id')}",
        f"  outcome    : {data.get('outcome')}",
        f"  issued_at  : {issued_s}",
        f"  synthetic  : {data.get('synthetic', True)}",
        "",
        "  Provider",
        f"    id      : {provider.get('provider_id')}",
        f"    network : {provider.get('network_id')}",
        f"    name    : {provider.get('display_name')}",
        "",
        "  HITL",
        f"    action  : {hitl.get('action')}",
        f"    actor   : {hitl.get('actor')}",
        f"    reason  : {hitl.get('reason') or '(none)'}",
        "",
        f"  Claims snapshot ({len(claims)})",
    ]
    for c in claims:
        lines.append(
            f"    • {c.get('claim_type')} = {c.get('value')!r} "
            f"(conf={c.get('confidence')}, ref={c.get('evidence_ref')})"
        )
    if run_series:
        lines.append("")
        lines.append(f"  Run-series stages ({len(run_series)})")
        for stage in run_series:
            lines.append(f"    → {stage}")
    lines.extend(
        [
            "",
            f"  Message: {data.get('message')}",
            "",
            "  NOTE: Synthetic demo receipt — not a production credentialing",
            "  decision. Not a HITRUST / HIPAA-certified audit packet.",
            "════════════════════════════════════════════════════════════",
            "",
        ]
    )
    return "\n".join(lines)


def write_receipt_artifacts(
    receipt: Union[ClaimReceipt, Mapping[str, Any]],
    directory: Path,
    *,
    stem: str = "receipt",
) -> dict[str, Path]:
    """Write JSON + text artifacts for fail-soft / deck capture."""
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / f"{stem}.json"
    text_path = directory / f"{stem}.txt"
    json_path.write_text(format_receipt_json(receipt), encoding="utf-8")
    text_path.write_text(format_receipt_text(receipt), encoding="utf-8")
    return {"json": json_path, "txt": text_path}
