"""F2/F3 SuperNode AgentApp stubs — fixtures only (no live SuperGrid)."""

from __future__ import annotations

import json
import unittest

from poppy_orchestrator.agent_app import build_grid_clients, kickoff_credentialing
from poppy_orchestrator.contracts.claims import (
    HOSPITAL_CRED_CLAIMS,
    PAYER_ENROLLMENT_CLAIMS,
)
from poppy_orchestrator.events.emit import LocalEventBus
from poppy_orchestrator.grid.fake_grid import FakeAgentGrid
from poppy_orchestrator.grid.handoff import run_grid_role_handoff
from poppy_orchestrator.hitl.pause import AutoApproveHitlGate
from poppy_orchestrator.supernodes.claim_service import (
    handle_inbound_message,
    roles_claim_slices,
    serve_claims_for_role,
)
from poppy_orchestrator.supernodes import hospital_cred_app, payer_enrollment_app


class TestF2F3SupernodeStubs(unittest.TestCase):
    def test_slices_are_disjoint(self) -> None:
        slices = roles_claim_slices()
        hosp = set(slices["HospitalCred"])
        pay = set(slices["PayerEnrollment"])
        self.assertEqual(hosp, set(HOSPITAL_CRED_CLAIMS))
        self.assertEqual(pay, set(PAYER_ENROLLMENT_CLAIMS))
        self.assertFalse(hosp & pay)

    def test_hospital_cred_happy_path(self) -> None:
        resp = serve_claims_for_role(
            "HospitalCred", provider_id="SYNTH-NPI-1999999999"
        )
        self.assertTrue(resp.ok)
        self.assertTrue(resp.synthetic)
        types = {c.claim_type for c in resp.claims}
        self.assertIn("work_history_complete", types)
        wh = next(c for c in resp.claims if c.claim_type == "work_history_complete")
        self.assertIs(wh.value, True)

    def test_payer_enrollment_happy_path(self) -> None:
        resp = serve_claims_for_role(
            "PayerEnrollment", provider_id="SYNTH-NPI-1999999999"
        )
        self.assertTrue(resp.ok)
        types = {c.claim_type for c in resp.claims}
        self.assertTrue(
            {"license_active", "npi_enumerated", "exclusion_clear"} <= types
        )

    def test_escalate_provider_fixture(self) -> None:
        hosp = serve_claims_for_role(
            "HospitalCred", provider_id="SYNTH-NPI-1888888888"
        )
        pay = serve_claims_for_role(
            "PayerEnrollment", provider_id="SYNTH-NPI-1888888888"
        )
        self.assertTrue(hosp.ok and pay.ok)
        wh = next(
            c for c in hosp.claims if c.claim_type == "work_history_complete"
        )
        ex = next(c for c in pay.claims if c.claim_type == "exclusion_clear")
        self.assertIs(wh.value, False)
        self.assertIs(ex.value, False)

    def test_agentapp_serve_payload_json(self) -> None:
        payload = {
            "provider_id": "SYNTH-NPI-1999999999",
            "network_id": "SYNTH-NETWORK-X",
            "synthetic": True,
        }
        h = json.loads(hospital_cred_app.serve_payload(payload))
        p = json.loads(payer_enrollment_app.serve_payload(payload))
        self.assertTrue(h["ok"] and p["ok"])
        self.assertEqual(h["source_node"], "HospitalCred")
        self.assertEqual(p["source_node"], "PayerEnrollment")

    def test_handle_inbound_unknown_role(self) -> None:
        raw = handle_inbound_message("NotARole", {"provider_id": "x"})
        data = json.loads(raw)
        self.assertFalse(data["ok"])

    def test_fake_grid_uses_claim_service(self) -> None:
        grid = FakeAgentGrid()
        result = run_grid_role_handoff(
            grid,
            provider_id="SYNTH-NPI-1999999999",
            network_id="SYNTH-NETWORK-X",
            sample_size=2,
        )
        self.assertTrue(result.ok)
        self.assertGreaterEqual(len(result.replies), 2)
        for reply in result.replies:
            body = json.loads(reply["payload"])
            self.assertTrue(body.get("ok"))
            self.assertTrue(body.get("synthetic"))
            self.assertIn(body["source_node"], {"HospitalCred", "PayerEnrollment"})

    def test_grid_clients_orchestrator_path(self) -> None:
        hospital, payer = build_grid_clients(FakeAgentGrid())
        bus = LocalEventBus()
        result = kickoff_credentialing(
            provider_id="SYNTH-NPI-1999999999",
            hospital=hospital,
            payer=payer,
            hitl_gate=AutoApproveHitlGate(),
            emitter=bus,
        )
        self.assertIsNotNone(result.receipt)
        self.assertEqual(result.outcome.value, "credentialed")
        self.assertFalse(result.bundle.missing_nodes())


if __name__ == "__main__":
    unittest.main()
