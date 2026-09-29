"""F0 Collaborative AgentApp Grid tools — ≥2 role handoff (synthetic)."""

from __future__ import annotations

import json
import tomllib
import unittest
from pathlib import Path

from poppy_orchestrator.agent_app import run_f0_grid_handoff
from poppy_orchestrator.events.emit import LocalEventBus
from poppy_orchestrator.grid import (
    ROLE_HOSPITAL_CRED,
    ROLE_PAYER_ENROLLMENT,
    FakeAgentGrid,
    FakeGridNode,
    run_grid_role_handoff,
)

ROOT = Path(__file__).resolve().parents[1]


class TestF0GridTools(unittest.TestCase):
    def test_fake_grid_tools_surface(self) -> None:
        grid = FakeAgentGrid()
        names = {t["name"] for t in grid.tools()}
        self.assertIn("get_nodes", names)
        self.assertIn("push_messages", names)
        self.assertIn("pull_messages", names)

    def test_get_nodes_returns_at_least_two(self) -> None:
        grid = FakeAgentGrid()
        out = json.loads(
            grid.call(
                {
                    "name": "get_nodes",
                    "call_id": "t1",
                    "arguments": {"sample_size": None},
                }
            )["output"]
        )
        self.assertGreaterEqual(out["num_available"], 2)
        self.assertGreaterEqual(len(out["nodes"]), 2)

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

        # Replies carry synthetic claim JSON (F5/F6 contract), not plain ACK text.
        roles_seen: set[str] = set()
        for reply in result.replies:
            payload = json.loads(reply["payload"])
            self.assertTrue(payload.get("synthetic"))
            self.assertTrue(payload.get("ok"))
            self.assertIn("claims", payload)
            self.assertGreaterEqual(len(payload["claims"]), 1)
            roles_seen.add(payload["source_node"])
        self.assertEqual(roles_seen, {ROLE_HOSPITAL_CRED, ROLE_PAYER_ENROLLMENT})

        stages = [
            e["data"]["stage"]
            for e in bus.events
            if e.get("event") == "privcred.stage"
        ]
        self.assertIn("grid.get_nodes", stages)
        self.assertIn("grid.push_messages", stages)
        self.assertIn("grid.pull_messages", stages)
        self.assertIn("grid.handoff.complete", stages)

        grid_events = {e.get("event") for e in bus.events}
        self.assertIn("privcred.grid.get_nodes", grid_events)
        self.assertIn("privcred.grid.push", grid_events)
        self.assertIn("privcred.grid.pull", grid_events)
        self.assertIn("privcred.grid.handoff", grid_events)

        tool_names = [e["name"] for e in grid.events if e.get("type") == "function_call"]
        self.assertEqual(tool_names.count("get_nodes"), 1)
        self.assertEqual(tool_names.count("push_messages"), 1)
        self.assertEqual(tool_names.count("pull_messages"), 1)

    def test_sample_miss_retries_full_list(self) -> None:
        nodes = [
            FakeGridNode("1", ROLE_HOSPITAL_CRED),
            FakeGridNode("2", ROLE_PAYER_ENROLLMENT),
            FakeGridNode("3", "OtherNode"),
        ]
        grid = FakeAgentGrid(nodes=nodes)
        result = run_grid_role_handoff(grid, sample_size=1, pull_timeout=0.0)
        self.assertTrue(result.ok)
        self.assertEqual(
            set(result.roles_contacted), {ROLE_HOSPITAL_CRED, ROLE_PAYER_ENROLLMENT}
        )

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

    def test_pyproject_agentapp_only_no_server_client(self) -> None:
        """F0 AC: AgentApp-only FAB — no ServerApp/ClientApp mix."""
        pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
        components = pyproject.get("tool", {}).get("flwr", {}).get("app", {}).get(
            "components", {}
        )
        self.assertIn("agentapp", components)
        self.assertNotIn("serverapp", components)
        self.assertNotIn("clientapp", components)
        # Also guard against accidental ServerApp/ClientApp strings in components
        blob = json.dumps(components).lower()
        self.assertNotIn("serverapp", blob)
        self.assertNotIn("clientapp", blob)


if __name__ == "__main__":
    unittest.main()
