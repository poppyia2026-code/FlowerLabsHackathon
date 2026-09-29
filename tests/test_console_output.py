"""Local entry points print on a terminal or pipe that is not UTF-8."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def run(*args: str) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k not in {"PYTHONUTF8"}}
    env.update({"PYTHONIOENCODING": "ascii", "ENDEAVOR_ENABLED": "0"})
    return subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
    )


@pytest.mark.parametrize(
    "command",
    [
        ("scripts/run_f9_e2e.py", "--hitl", "approve"),
        ("scripts/print_receipt.py",),
        ("scripts/run_g3_failsoft.py",),
        ("scripts/dry_run.py",),
        ("scripts/run_f5.py",),
        ("-m", "poppy_orchestrator"),
    ],
    ids=lambda c: " ".join(c),
)
def test_entry_point_survives_an_ascii_console(command: tuple[str, ...]) -> None:
    result = run(*command)

    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")[-600:]
    assert b"UnicodeEncodeError" not in result.stderr


def test_receipt_frame_is_written_as_utf8() -> None:
    result = run("scripts/print_receipt.py")

    assert "AUDITABLE CLAIM RECEIPT" in result.stdout.decode("utf-8")
    assert "╔" in result.stdout.decode("utf-8")
