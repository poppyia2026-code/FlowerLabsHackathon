"""F9 / FLOWER-14 — E2E dry run fixtures→orchestrator→2 claims→HITL→receipt."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_f9_e2e.py"


def _run(env_extra: dict | None = None, args: list[str] | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    # Ensure clean auto-driver unless test sets it
    env.pop("TEST_HITL_DECISION", None)
    env.pop("PRIVCRED_E2E_TEST", None)
    if env_extra:
        env.update(env_extra)
    # None → default CLI preset; explicit [] → script defaults (auto-env mode)
    argv = ["--hitl", "approve", "--budget-check"] if args is None else args
    cmd = [sys.executable, str(SCRIPT), *argv]
    return subprocess.run(
        cmd,
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


class TestF9E2E:
    def test_happy_path_script_passes_budget(self) -> None:
        proc = _run()
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert "F9 E2E DRY-RUN SUMMARY" in proc.stdout
        assert "live_supergrid" in proc.stdout
        assert '"live_supergrid": false' in proc.stdout.lower() or '"live_supergrid": false' in proc.stdout
        assert "receipt" in proc.stdout

    def test_ci_env_driver_requires_privcred_e2e_flag(self) -> None:
        # TEST_HITL_DECISION alone must be refused (production never auto via env)
        proc = _run(
            env_extra={"TEST_HITL_DECISION": "approve"},
            args=[],  # auto-env mode
        )
        assert proc.returncode != 0
        assert "PRIVCRED_E2E_TEST" in (proc.stderr + proc.stdout)

    def test_ci_env_driver_with_flag_ok(self) -> None:
        proc = _run(
            env_extra={
                "TEST_HITL_DECISION": "approve",
                "PRIVCRED_E2E_TEST": "1",
            },
            args=["--budget-check"],
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert "TEST_HITL_DECISION=approve" in proc.stdout

    def test_approve_emits_receipt_json(self, tmp_path: Path) -> None:
        out = tmp_path / "f9.json"
        proc = _run(args=["--hitl", "approve", "--budget-check", "--json-out", str(out)])
        assert proc.returncode == 0, proc.stdout + proc.stderr
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["f9_e2e"] is True
        assert data["live_supergrid"] is False
        assert data["production_auto_approve"] is False
        assert data["receipt_emitted"] is True
        assert data["claim_count"] >= 2
        assert "license_active" in data["claim_types"]
        assert "work_history_complete" in data["claim_types"]
        assert data["budget"]["machine_ok"] is True
        assert "endeavor_assist" in data["stages"]
        assert data["roles"]["live_dress"] == "G2 / Leandro+Franco"

    def test_escalate_no_receipt(self, tmp_path: Path) -> None:
        out = tmp_path / "f9-esc.json"
        proc = _run(args=["--hitl", "escalate", "--json-out", str(out)])
        assert proc.returncode == 0, proc.stdout + proc.stderr
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["receipt_emitted"] is False
        assert data["hitl"]["action"] == "escalate"
