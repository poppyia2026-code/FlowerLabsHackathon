"""Flower Endeavor model wiring for PoppyOrchestrator (F11 / FLOWER-7).

Honest contract:
  - Live calls only when Flower runtime or explicit API credentials exist.
  - Without a key → dry-run stub with endeavor_optional=True (never fake live).
  - Synthetic prompts/fixtures only — no PHI / CAQH / NPDB.
"""

from poppy_orchestrator.endeavor.client import EndeavorClient, EndeavorResult
from poppy_orchestrator.endeavor.config import EndeavorConfig, resolve_endeavor_config
from poppy_orchestrator.endeavor.summarize import summarize_claims_for_hitl

__all__ = [
    "EndeavorClient",
    "EndeavorConfig",
    "EndeavorResult",
    "resolve_endeavor_config",
    "summarize_claims_for_hitl",
]
