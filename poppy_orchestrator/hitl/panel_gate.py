"""F7 PanelHitlGate — blocks claim completion until human Approve/Escalate/Reject.

Wires the F6 fail-closed pause to a claim review panel (CLI or local HTTP UI).
Never auto-approves. After Approve only, orchestrator emits F8 receipt.
"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Optional
from urllib.parse import urlparse
import json
import threading
import time

from poppy_orchestrator.contracts.claims import ClaimBundle, HitlDecision
from poppy_orchestrator.events.emit import EventEmitter, emit_text
from poppy_orchestrator.hitl.panel import (
    HitlParseError,
    bundle_to_panel_view,
    decision_from_raw,
    render_panel_html,
    render_panel_text,
)
from poppy_orchestrator.hitl.pause import HitlGate, _emit_hitl_request


class PanelHitlGate(HitlGate):
    """Block until a human decision is delivered via wait_fn / queue.

    ``wait_fn(panel_view_dict, timeout_s) -> decision dict|str``
    Must not return until the operator acts. Empty / invalid → re-prompt
    is the wait_fn's responsibility; this gate still refuses empty actions
    via ``decision_from_raw``.
    """

    def __init__(
        self,
        wait_fn: Callable[[dict, Optional[float]], Any],
        *,
        actor: str = "hitl-panel",
    ) -> None:
        self._wait_fn = wait_fn
        self._actor = actor
        self.last_view: Optional[dict] = None
        self.wait_started_at: Optional[float] = None
        self.wait_elapsed_s: Optional[float] = None

    def wait_for_decision(
        self,
        bundle: ClaimBundle,
        emitter: EventEmitter,
        *,
        timeout_s: Optional[float] = None,
    ) -> HitlDecision:
        view = bundle_to_panel_view(bundle)
        self.last_view = view.to_dict()
        _emit_hitl_request(emitter, bundle)
        emit_text(emitter, render_panel_text(view))
        self.wait_started_at = time.time()
        raw = self._wait_fn(view.to_dict(), timeout_s)
        decision = decision_from_raw(raw, default_actor=self._actor)
        self.wait_elapsed_s = time.time() - self.wait_started_at
        emitter.emit({"event": "privcred.hitl.decision", "data": decision.to_dict()})
        emit_text(
            emitter,
            f"HITL panel decision: {decision.action.value} "
            f"(operator≈{self.wait_elapsed_s:.1f}s, actor={decision.actor})",
        )
        return decision


class DecisionQueue:
    """Thread-safe one-shot decision mailbox for the HTTP / CLI panel."""

    def __init__(self) -> None:
        self._event = threading.Event()
        self._lock = threading.Lock()
        self._decision: Optional[dict] = None
        self._panel: Optional[dict] = None

    def set_panel(self, panel: dict) -> None:
        with self._lock:
            self._panel = panel
            self._decision = None
            self._event.clear()

    def get_panel(self) -> Optional[dict]:
        with self._lock:
            return dict(self._panel) if self._panel else None

    def submit(self, decision: dict) -> HitlDecision:
        parsed = decision_from_raw(decision, default_actor="hitl-web-panel")
        with self._lock:
            self._decision = parsed.to_dict()
            self._event.set()
        return parsed

    def wait(self, timeout_s: Optional[float] = None) -> dict:
        ok = self._event.wait(timeout=timeout_s)
        if not ok:
            raise TimeoutError("HITL panel timed out waiting for human decision")
        with self._lock:
            if self._decision is None:
                raise RuntimeError("HITL decision missing after event set")
            return dict(self._decision)


def console_panel_wait_fn(
    input_fn: Callable[[str], str] = input,
) -> Callable[[dict, Optional[float]], dict]:
    """CLI wait_fn: print panel, re-prompt until valid action (no default)."""

    def wait_fn(panel: dict, timeout_s: Optional[float]) -> dict:
        # timeout_s reserved for future non-blocking CLI; stdin is interactive
        _ = timeout_s
        from poppy_orchestrator.hitl.panel import PanelView

        view = PanelView(
            run_id=str(panel["run_id"]),
            provider_id=str(panel["provider"]["provider_id"]),
            network_id=str(panel["provider"]["network_id"]),
            display_name=str(panel["provider"]["display_name"]),
            claims=tuple(panel.get("claims") or ()),
            missing_nodes=tuple(panel.get("missing_nodes") or ()),
        )
        print("\n" + render_panel_text(view))
        while True:
            try:
                raw = input_fn("> ").strip()
                action = decision_from_raw(
                    {"action": raw, "actor": "console-panel", "reason": f"console:{raw}"}
                )
                return action.to_dict()
            except HitlParseError as exc:
                print(f"  ! {exc} — try again")

    return wait_fn


class HttpPanelServer:
    """Tiny stdlib HTTP server: GET / panel, POST /decide action."""

    def __init__(
        self,
        queue: DecisionQueue,
        *,
        host: str = "127.0.0.1",
        port: int = 8765,
    ) -> None:
        self.queue = queue
        self.host = host
        self.port = port
        self._httpd: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        gate_queue = queue

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt: str, *args: Any) -> None:  # quieter demos
                return

            def _json(self, code: int, payload: dict) -> None:
                body = json.dumps(payload).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self) -> None:  # noqa: N802
                path = urlparse(self.path).path
                if path in {"/", "/index.html", "/panel"}:
                    panel = gate_queue.get_panel()
                    if panel is None:
                        html_body = (
                            "<!DOCTYPE html><html><body><h1>HITL panel</h1>"
                            "<p>Waiting for claim bundle…</p></body></html>"
                        )
                    else:
                        from poppy_orchestrator.hitl.panel import PanelView

                        view = PanelView(
                            run_id=str(panel["run_id"]),
                            provider_id=str(panel["provider"]["provider_id"]),
                            network_id=str(panel["provider"]["network_id"]),
                            display_name=str(panel["provider"]["display_name"]),
                            claims=tuple(panel.get("claims") or ()),
                            missing_nodes=tuple(panel.get("missing_nodes") or ()),
                        )
                        html_body = render_panel_html(view)
                    data = html_body.encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                if path == "/health":
                    self._json(200, {"ok": True, "pending": gate_queue.get_panel() is not None})
                    return
                if path == "/panel.json":
                    panel = gate_queue.get_panel()
                    if panel is None:
                        self._json(404, {"error": "no pending panel"})
                    else:
                        self._json(200, panel)
                    return
                self._json(404, {"error": "not found"})

            def do_POST(self) -> None:  # noqa: N802
                path = urlparse(self.path).path
                if path != "/decide":
                    self._json(404, {"error": "not found"})
                    return
                length = int(self.headers.get("Content-Length", "0"))
                raw_body = self.rfile.read(length) if length else b"{}"
                try:
                    payload = json.loads(raw_body.decode("utf-8") or "{}")
                    decision = gate_queue.submit(payload)
                    self._json(200, decision.to_dict())
                except (HitlParseError, json.JSONDecodeError, ValueError, TypeError) as exc:
                    self._json(400, {"error": str(exc)})

        self._handler_cls = Handler

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}/"

    def start(self) -> str:
        self._httpd = ThreadingHTTPServer((self.host, self.port), self._handler_cls)
        self.port = self._httpd.server_address[1]
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        return self.url

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None


def make_http_panel_gate(
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    timeout_s: Optional[float] = 300.0,
) -> tuple[PanelHitlGate, HttpPanelServer, DecisionQueue]:
    """Build PanelHitlGate + HTTP server pair for judge-visible demos."""
    queue = DecisionQueue()
    server = HttpPanelServer(queue, host=host, port=port)

    def wait_fn(panel: dict, wait_timeout: Optional[float]) -> dict:
        queue.set_panel(panel)
        effective = wait_timeout if wait_timeout is not None else timeout_s
        print(f"\nHITL panel ready: {server.url}")
        print("Open the URL, review claims, then Approve / Escalate / Reject.")
        print("Flow is paused until a human acts (auto-approve disabled).\n")
        return queue.wait(timeout_s=effective)

    gate = PanelHitlGate(wait_fn=wait_fn, actor="hitl-web-panel")
    return gate, server, queue
