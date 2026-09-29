"""Every package loads on its own, whichever one is imported first."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "module",
    [
        "poppy_orchestrator.agent_app",
        "poppy_orchestrator.clients",
        "poppy_orchestrator.grid",
        "poppy_orchestrator.live_runtime",
        "poppy_orchestrator.supernodes",
        "poppy_orchestrator.supernodes.runtime",
        "poppy_orchestrator.supernodes.hospital_cred_app",
        "poppy_orchestrator.supernodes.payer_enrollment_app",
        "poppy_orchestrator.supernodes.wording",
    ],
)
def test_module_imports_in_a_fresh_interpreter(module: str) -> None:
    result = subprocess.run(
        [sys.executable, "-c", f"import {module}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr[-400:]
