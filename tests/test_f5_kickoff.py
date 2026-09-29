"""F5 smoke: kickoff P for network X → both nodes → HITL → receipt."""

from __future__ import annotations

import unittest

from poppy_orchestrator.agent_app import kickoff_credentialing
from poppy_orchestrator.contracts.claims import CredentialingOutcome, HitlAction
from poppy_orchestrator.events.emit import LocalEventBus, NullEmitter
from poppy_orchestrator.hitl.pause import CallbackHitlGate
from poppy_orchestrator.orchestration.flow import FLOW_STAGES


def _preset(action: HitlAction) -> CallbackHitlGate:
    def wait_fn(bundle: dict, timeout_s):
        return {
            "action": action.value,
            "actor": "f5-test",
            "reason": f"test:{action.value}",
        }

    return CallbackHitlGate(wait_fn=wait_fn)


class TestF5Kickoff(unittest.TestCase):
    def test_happy_path_provider_p_yields_receipt(self) -> None:
        bus = LocalEventBus()
        result = kickoff_credentialing(
            provider_id="SYNTH-NPI-1999999999",
            network_id="SYNTH-NETWORK-X",
            emitter=bus,
            hitl_gate=_preset(HitlAction.APPROVE),
        )
        self.assertEqual(result.outcome, CredentialingOutcome.CREDENTIALED)
        self.assertIsNotNone(result.hitl)
        self.assertIsNotNone(result.receipt)
        self.assertEqual(result.bundle.provider.network_id, "SYNTH-NETWORK-X")
        self.assertIn("Provider P", result.bundle.provider.display_name)
        self.assertEqual(result.bundle.missing_nodes(), [])
        claim_types = {c.claim_type for c in result.bundle.all_claims()}
        self.assertIn("work_history_complete", claim_types)
        self.assertIn("license_active", claim_types)

        stages = [
            e["data"]["stage"]
            for e in bus.events
            if e.get("event") == "privcred.stage"
        ]
        self.assertIn("kickoff", stages)
        self.assertIn("hitl_pause", stages)
        self.assertIn("claim_receipt", stages)
        self.assertIn("complete", stages)
        self.assertTrue(
            any(e.get("event") == "privcred.hitl.request" for e in bus.events)
        )
        self.assertTrue(
            any(e.get("event") == "privcred.claim_receipt" for e in bus.events)
        )

    def test_escalate_path_no_receipt(self) -> None:
        result = kickoff_credentialing(
            provider_id="SYNTH-NPI-1888888888",
            network_id="SYNTH-NETWORK-X",
            emitter=NullEmitter(),
            hitl_gate=_preset(HitlAction.ESCALATE),
        )
        self.assertEqual(result.outcome, CredentialingOutcome.ESCALATED)
        self.assertIsNone(result.receipt)
        self.assertIsNotNone(result.hitl)

    def test_flow_stages_documented(self) -> None:
        self.assertEqual(FLOW_STAGES[0], "kickoff")
        self.assertIn("hitl_pause", FLOW_STAGES)
        self.assertEqual(FLOW_STAGES[-1], "complete")


if __name__ == "__main__":
    unittest.main()
