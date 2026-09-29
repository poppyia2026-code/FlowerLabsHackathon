"""F0 Collaborative AgentApp Grid tools — ≥2 role handoff (synthetic)."""

from __future__ import annotations

import unittest

from poppy_orchestrator.agent_app import run_f0_grid_handoff
from poppy_orchestrator.events.emit import LocalEventBus
from poppy_orchestrator.grid import (
    ROLE_HOSPITAL_CRED,
    ROLE_PAYER_ENROLLMENT,
    FakeAgentGrid,
    FakeGridNode,
    run_grid_role_handoff,
)


class TestF0GridTools(unittest.TestCase):
    def test_fake_grid_tools_surface(self) -> None:
        grid = FakeAgentGrid()
        names = {t["name"] for t in grid.tools()}
        self.assertIn("get_nodes", names)
        self.assertIn("push_messages", names)
        self.assertIn("pull_messages", names)

    def test_handoff_contacts_both_roles(self) -> None:
        bus = LocalEventBus()
        grid = FakeAgentGrid()
        result = run_grid_role_handoff(
            grid,
            provider_id="SYNTH-NPI-1999999999",
            network_id="SYNTH-NETWORK-X",
            sample_size=2,
            emitter=bus,
        )
        self.assertTrue(result.ok)
        self.assertIn(ROLE_HOSPITAL_CRED, result.roles_contacted)
        self.assertIn(ROLE_PAYER_ENROLLMENT, result.roles_contacted)
        self.assertGreaterEqual(len(result.replies), 2)
        stages = [
            e["data"]["stage"]
            for e in bus.events
            if e.get("event") == "privcred.stage"
        ]
        self.assertIn("grid.get_nodes", stages)
        self.assertIn("grid.push_messages", stages)
        self.assertIn("grid.pull_messages", stages)
        self.assertIn("grid.handoff.complete", stages)
        # Tool calls emitted on FakeAgentGrid event stream (judge-visible analogue)
        tool_names = [e["name"] for e in grid.events if e.get("type") == "function_call"]
        self.assertEqual(tool_names.count("get_nodes"), 1)
        self.assertEqual(tool_names.count("push_messages"), 1)
        self.assertEqual(tool_names.count("pull_messages"), 1)

    def test_sample_miss_retries_full_list(self) -> None:
        # Three nodes; sample_size=1 may miss a role → handoff retries full list.
        nodes = [
            FakeGridNode("1", ROLE_HOSPITAL_CRED),
            FakeGridNode("2", ROLE_PAYER_ENROLLMENT),
            FakeGridNode("3", "OtherNode"),
        ]
        grid = FakeAgentGrid(nodes=nodes)
        result = run_grid_role_handoff(grid, sample_size=1, pull_timeout=0.0)
        self.assertTrue(result.ok)
        self.assertEqual(set(result.roles_contacted), {ROLE_HOSPITAL_CRED, ROLE_PAYER_ENROLLMENT})

    def test_missing_roles_fails(self) -> None:
        grid = FakeAgentGrid(nodes=[FakeGridNode("1", ROLE_HOSPITAL_CRED)])
        result = run_grid_role_handoff(grid, sample_size=None)
        self.assertFalse(result.ok)
        self.assertIn(ROLE_PAYER_ENROLLMENT, result.missing_roles)

    def test_agent_app_helper_defaults_to_fake_grid(self) -> None:
        result = run_f0_grid_handoff(
            provider_id="SYNTH-NPI-1999999999",
            network_id="SYNTH-NETWORK-X",
        )
        self.assertTrue(result.ok)
        summary = result.to_summary()
        self.assertTrue(summary["synthetic"])
        self.assertGreaterEqual(summary["reply_count"], 2)


if __name__ == "__main__":
    unittest.main()
