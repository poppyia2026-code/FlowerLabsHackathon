"""F7 (FLOWER-3): HITL claim review panel — Approve / Escalate / Reject.

AC: panel shows typed claims; all three actions required before complete;
never auto-approve; Approve → F8 receipt; Escalate/Reject → no receipt;
happy-path operator budget documented at <60s.
"""

from __future__ import annotations

import json
import threading
import time
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pytest

from poppy_orchestrator.clients.hospital_cred import StubHospitalCredClient
from poppy_orchestrator.clients.payer_enrollment import StubPayerEnrollmentClient
from poppy_orchestrator.contracts.claims import (
    CredentialingOutcome,
    HitlAction,
)
from poppy_orchestrator.events.emit import LocalEventBus
from poppy_orchestrator.hitl.panel import (
    HitlParseError,
    bundle_to_panel_view,
    decision_from_raw,
    parse_hitl_action,
    render_panel_html,
    render_panel_text,
)
from poppy_orchestrator.hitl.panel_gate import (
    DecisionQueue,
    HttpPanelServer,
    PanelHitlGate,
    console_panel_wait_fn,
    make_http_panel_gate,
)
from poppy_orchestrator.hitl.pause import AutoApproveHitlGate
from poppy_orchestrator.orchestration.flow import OrchestratorConfig, run_credentialing_flow


def _run_with_gate(gate, provider_id: str = "SYNTH-NPI-1999999999"):
    bus = LocalEventBus()
    result = run_credentialing_flow(
        hospital=StubHospitalCredClient(),
        payer=StubPayerEnrollmentClient(),
        hitl_gate=gate,
        emitter=bus,
        config=OrchestratorConfig(provider_id=provider_id),
    )
    return result, bus


def _scripted_gate(action: str) -> PanelHitlGate:
    def wait_fn(panel: dict, timeout_s: Optional[float]):
        _ = timeout_s
        assert panel["auto_approve"] is False
        assert set(panel["actions"]) == {"approve", "escalate", "reject"}
        assert panel["provider"]["provider_id"].startswith("SYNTH-")
        assert len(panel["claims"]) >= 1
        return {"action": action, "actor": "f7-test", "reason": f"test:{action}"}

    return PanelHitlGate(wait_fn=wait_fn, actor="f7-test")


# --- parse / never auto-approve ---


def test_parse_rejects_empty_never_auto_approve():
    with pytest.raises(HitlParseError):
        parse_hitl_action("")
    with pytest.raises(HitlParseError):
        parse_hitl_action("   ")
    with pytest.raises(HitlParseError):
        parse_hitl_action("maybe")
    with pytest.raises(HitlParseError):
        decision_from_raw({"action": ""})


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("approve", HitlAction.APPROVE),
        ("a", HitlAction.APPROVE),
        ("escalate", HitlAction.ESCALATE),
        ("e", HitlAction.ESCALATE),
        ("reject", HitlAction.REJECT),
        ("r", HitlAction.REJECT),
    ],
)
def test_parse_all_three_actions(raw, expected):
    assert parse_hitl_action(raw) == expected


def test_console_wait_fn_reprompts_until_valid():
    answers = iter(["", "nope", "approve"])

    def fake_input(_prompt: str) -> str:
        return next(answers)

    wait_fn = console_panel_wait_fn(input_fn=fake_input)
    panel = {
        "run_id": "run-test",
        "provider": {
            "provider_id": "SYNTH-NPI-1999999999",
            "network_id": "SYNTH-NETWORK-X",
            "display_name": "Synthetic Provider P",
        },
        "claims": [{"claim_type": "license_active", "value": True, "confidence": 1.0}],
        "missing_nodes": [],
        "actions": ["approve", "escalate", "reject"],
        "auto_approve": False,
    }
    decision = wait_fn(panel, None)
    assert decision["action"] == "approve"
    assert decision["actor"] == "console-panel"


# --- panel render ---


def test_panel_view_shows_typed_claims_for_provider_p():
    gate = _scripted_gate("approve")
    result, bus = _run_with_gate(gate)
    assert gate.last_view is not None
    view = gate.last_view
    assert view["provider"]["display_name"]
    assert view["provider"]["provider_id"] == "SYNTH-NPI-1999999999"
    claim_types = {c["claim_type"] for c in view["claims"]}
    assert "license_active" in claim_types or "work_history_complete" in claim_types
    assert view["operator_budget_s"] == 60
    assert view["auto_approve"] is False

    text = render_panel_text(bundle_to_panel_view(result.bundle))
    assert "Approve" in text or "approve" in text
    assert "auto-approve" in text.lower() or "DISABLED" in text
    assert "60" in text

    html = render_panel_html(bundle_to_panel_view(result.bundle))
    assert "Approve" in html and "Escalate" in html and "Reject" in html
    assert "auto-approve OFF" in html


# --- three actions through PanelHitlGate + F8 wiring ---


def test_approve_blocks_until_panel_then_emits_receipt():
    gate = _scripted_gate("approve")
    result, bus = _run_with_gate(gate)
    assert result.hitl is not None
    assert result.hitl.action == HitlAction.APPROVE
    assert result.outcome == CredentialingOutcome.CREDENTIALED
    assert result.receipt is not None
    assert any(e.get("event") == "privcred.hitl.request" for e in bus.events)
    assert any(e.get("event") == "privcred.claim_receipt" for e in bus.events)
    assert gate.wait_elapsed_s is not None
    # Scripted path is near-instant; budget doc is 60s for human operators
    assert gate.wait_elapsed_s < 60


def test_escalate_no_receipt():
    gate = _scripted_gate("escalate")
    result, bus = _run_with_gate(gate, provider_id="SYNTH-NPI-1888888888")
    assert result.hitl.action == HitlAction.ESCALATE
    assert result.outcome == CredentialingOutcome.ESCALATED
    assert result.receipt is None
    assert not any(e.get("event") == "privcred.claim_receipt" for e in bus.events)
    assert any(e.get("event") == "privcred.hitl.request" for e in bus.events)


def test_reject_no_receipt():
    gate = _scripted_gate("reject")
    result, bus = _run_with_gate(gate)
    assert result.hitl.action == HitlAction.REJECT
    assert result.outcome == CredentialingOutcome.REJECTED
    assert result.receipt is None
    assert not any(e.get("event") == "privcred.claim_receipt" for e in bus.events)


def test_panel_path_is_not_auto_approve_gate():
    """F7 live path must use PanelHitlGate, not AutoApproveHitlGate."""
    assert not isinstance(_scripted_gate("approve"), AutoApproveHitlGate)
    # AutoApprove is still available for dry-run only — document separation
    auto = AutoApproveHitlGate()
    bus = LocalEventBus()
    # Ensure naming distinction: dry-run-auto actor must not appear on panel path
    from poppy_orchestrator.clients.hospital_cred import StubHospitalCredClient as H
    from poppy_orchestrator.clients.payer_enrollment import StubPayerEnrollmentClient as P

    result = run_credentialing_flow(
        hospital=H(),
        payer=P(),
        hitl_gate=auto,
        emitter=bus,
        config=OrchestratorConfig(),
    )
    assert result.hitl.actor == "dry-run-auto"
    panel_result, _ = _run_with_gate(_scripted_gate("approve"))
    assert panel_result.hitl.actor != "dry-run-auto"


# --- HTTP panel blocks until POST /decide ---


def test_http_panel_blocks_until_human_posts_decision():
    queue = DecisionQueue()
    server = HttpPanelServer(queue, host="127.0.0.1", port=0)
    url = server.start()
    try:
        def wait_fn(panel, timeout_s):
            queue.set_panel(panel)
            return queue.wait(timeout_s=timeout_s)

        gate = PanelHitlGate(wait_fn=wait_fn, actor="hitl-web-panel")

        outcome = {}

        def run_flow():
            result, bus = _run_with_gate(gate)
            outcome["result"] = result
            outcome["bus"] = bus

        t = threading.Thread(target=run_flow, daemon=True)
        t.start()

        # Wait until panel is pending
        deadline = time.time() + 5
        while time.time() < deadline and queue.get_panel() is None:
            time.sleep(0.05)
        assert queue.get_panel() is not None, "panel should be pending (flow blocked)"

        # GET panel HTML while blocked
        with urlopen(url, timeout=2) as resp:
            html = resp.read().decode("utf-8")
        assert "Approve" in html and "Reject" in html

        # Empty action rejected
        req = Request(
            url + "decide",
            data=json.dumps({"action": ""}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urlopen(req, timeout=2)
            raise AssertionError("empty action should 400")
        except HTTPError as exc:
            assert exc.code == 400

        # Still blocked
        assert t.is_alive()

        # Human Approve
        req = Request(
            url + "decide",
            data=json.dumps(
                {"action": "approve", "actor": "judge", "reason": "http-test"}
            ).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=2) as resp:
            body = json.loads(resp.read().decode())
        assert body["action"] == "approve"

        t.join(timeout=5)
        assert not t.is_alive()
        result = outcome["result"]
        assert result.hitl.action == HitlAction.APPROVE
        assert result.receipt is not None
    finally:
        server.stop()


def test_make_http_panel_gate_happy_path_under_budget():
    """Scripted POST after start — operator time well under 60s."""
    gate, server, queue = make_http_panel_gate(host="127.0.0.1", port=0, timeout_s=10)
    url = server.start()
    try:
        def clicker():
            deadline = time.time() + 5
            while time.time() < deadline and queue.get_panel() is None:
                time.sleep(0.02)
            req = Request(
                url + "decide",
                data=json.dumps({"action": "approve", "actor": "timer-test"}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urlopen(req, timeout=2)

        threading.Thread(target=clicker, daemon=True).start()
        result, _ = _run_with_gate(gate)
        assert result.receipt is not None
        assert gate.wait_elapsed_s is not None
        assert gate.wait_elapsed_s < 60
    finally:
        server.stop()
