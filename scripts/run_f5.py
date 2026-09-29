#!/usr/bin/env python3
"""F5 demo entry — thin wrapper around ``python -m poppy_orchestrator``.

Usage:
  python scripts/run_f5.py
  python scripts/run_f5.py --provider SYNTH-NPI-1999999999 --network SYNTH-NETWORK-X
  python scripts/run_f5.py --hitl escalate --provider SYNTH-NPI-1888888888

Synthetic fixtures only. Same path as AgentApp kickoff (FLOWER-6 / F5).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from poppy_orchestrator.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
