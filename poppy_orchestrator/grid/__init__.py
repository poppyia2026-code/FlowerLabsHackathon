"""F0 — Collaborative AgentApp Grid tools (Orchestrator ↔ SuperNode roles).

Uses Flower AgentGrid tool surface:
  get_nodes (sample) → push_messages → pull_messages

AgentApp-only FAB — never mix ServerApp/ClientApp.
Synthetic fixtures only.
"""

from poppy_orchestrator.grid.fake_grid import FakeAgentGrid, FakeGridNode
from poppy_orchestrator.grid.handoff import (
    GridHandoffResult,
    ROLE_HOSPITAL_CRED,
    ROLE_ORCHESTRATOR,
    ROLE_PAYER_ENROLLMENT,
    run_grid_role_handoff,
)

__all__ = [
    "FakeAgentGrid",
    "FakeGridNode",
    "GridHandoffResult",
    "ROLE_HOSPITAL_CRED",
    "ROLE_ORCHESTRATOR",
    "ROLE_PAYER_ENROLLMENT",
    "run_grid_role_handoff",
]
