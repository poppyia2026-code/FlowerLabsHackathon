"""F7 claim review panel — render typed claims + parse HITL actions.

Never auto-approves. Empty / unknown input is rejected until the human
chooses Approve, Escalate, or Reject explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional
import html
import json
import time

from poppy_orchestrator.contracts.claims import ClaimBundle, HitlAction, HitlDecision

# Aliases operators may type in the CLI panel
_ACTION_ALIASES: dict[str, HitlAction] = {
    "a": HitlAction.APPROVE,
    "approve": HitlAction.APPROVE,
    "approved": HitlAction.APPROVE,
    "e": HitlAction.ESCALATE,
    "escalate": HitlAction.ESCALATE,
    "escalated": HitlAction.ESCALATE,
    "r": HitlAction.REJECT,
    "reject": HitlAction.REJECT,
    "rejected": HitlAction.REJECT,
}


class HitlParseError(ValueError):
    """Raised when input is empty or not a valid HITL action (fail-closed)."""


def parse_hitl_action(raw: str) -> HitlAction:
    """Parse operator input into HitlAction. Never defaults to Approve."""
    key = (raw or "").strip().lower()
    if not key:
        raise HitlParseError("empty HITL action — choose approve, escalate, or reject")
    action = _ACTION_ALIASES.get(key)
    if action is None:
        raise HitlParseError(
            f"unknown HITL action {raw!r} — choose approve, escalate, or reject"
        )
    return action


def decision_from_raw(
    raw: Mapping[str, Any] | str,
    *,
    default_actor: str = "hitl-panel",
) -> HitlDecision:
    """Build HitlDecision from a dict (web/CLI JSON) or action string."""
    if isinstance(raw, str):
        action = parse_hitl_action(raw)
        return HitlDecision(action=action, actor=default_actor, reason="panel")
    action = parse_hitl_action(str(raw.get("action", "")))
    return HitlDecision(
        action=action,
        actor=str(raw.get("actor") or default_actor),
        reason=str(raw.get("reason") or "panel"),
        decided_at=float(raw.get("decided_at", time.time())),
    )


@dataclass(frozen=True)
class PanelView:
    """Structured claim panel payload for CLI / static UI / judges."""

    run_id: str
    provider_id: str
    network_id: str
    display_name: str
    claims: tuple[dict[str, Any], ...]
    missing_nodes: tuple[str, ...]
    actions: tuple[str, ...] = ("approve", "escalate", "reject")
    synthetic: bool = True
    operator_budget_s: int = 60

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "provider": {
                "provider_id": self.provider_id,
                "network_id": self.network_id,
                "display_name": self.display_name,
            },
            "claims": list(self.claims),
            "missing_nodes": list(self.missing_nodes),
            "actions": list(self.actions),
            "synthetic": self.synthetic,
            "operator_budget_s": self.operator_budget_s,
            "auto_approve": False,
        }


def bundle_to_panel_view(bundle: ClaimBundle) -> PanelView:
    """Map ClaimBundle → panel view (typed claims for synthetic provider P)."""
    claims = tuple(c.to_dict() for c in bundle.all_claims())
    return PanelView(
        run_id=bundle.run_id,
        provider_id=bundle.provider.provider_id,
        network_id=bundle.provider.network_id,
        display_name=bundle.provider.display_name,
        claims=claims,
        missing_nodes=tuple(bundle.missing_nodes()),
    )


def render_panel_text(view: PanelView) -> str:
    """CLI / Flower Chat text block judges can screenshot."""
    lines = [
        "=== HITL Claim Review Panel (F7) ===",
        f"Provider: {view.display_name} ({view.provider_id})",
        f"Network:  {view.network_id}",
        f"Run:      {view.run_id}",
        f"Budget:   <{view.operator_budget_s}s operator time (happy path)",
        "Synthetic fixtures only — no live CAQH/NPDB.",
        "Auto-approve: DISABLED (human action required).",
        "",
        "Typed claims:",
    ]
    if not view.claims:
        lines.append("  (none — node missing or empty slice)")
    for c in view.claims:
        evid = c.get("evidence_ref") or "-"
        lines.append(
            f"  * {c.get('claim_type')} = {c.get('value')!r}  "
            f"(confidence={c.get('confidence')}, evidence={evid})"
        )
    if view.missing_nodes:
        lines.append(f"! Missing nodes: {', '.join(view.missing_nodes)}")
    lines.extend(
        [
            "",
            "Actions (required before complete):",
            "  [a]pprove   → emit F8 receipt",
            "  [e]scalate  → no receipt",
            "  [r]eject    → no receipt",
            "Empty input is rejected (never auto-approve).",
        ]
    )
    return "\n".join(lines)


def render_panel_html(view: PanelView) -> str:
    """Self-contained static HTML panel for judges / local demo."""
    claims_rows = []
    for c in view.claims:
        claims_rows.append(
            "<tr>"
            f"<td>{html.escape(str(c.get('claim_type')))}</td>"
            f"<td><code>{html.escape(repr(c.get('value')))}</code></td>"
            f"<td>{html.escape(str(c.get('confidence')))}</td>"
            f"<td>{html.escape(str(c.get('evidence_ref') or '-'))}</td>"
            "</tr>"
        )
    if not claims_rows:
        claims_rows.append(
            '<tr><td colspan="4"><em>No claims — check missing nodes</em></td></tr>'
        )
    missing = (
        f"<p class='warn'><strong>Missing nodes:</strong> "
        f"{html.escape(', '.join(view.missing_nodes))}</p>"
        if view.missing_nodes
        else ""
    )
    payload = html.escape(json.dumps(view.to_dict(), indent=2))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>PrivCred HITL Claim Panel (F7)</title>
  <style>
    :root {{ font-family: ui-sans-serif, system-ui, sans-serif; color: #0f172a; }}
    body {{ max-width: 880px; margin: 2rem auto; padding: 0 1rem; background: #f8fafc; }}
    h1 {{ font-size: 1.35rem; margin-bottom: 0.25rem; }}
    .meta {{ color: #475569; font-size: 0.95rem; margin-bottom: 1rem; }}
    .badge {{ display:inline-block; background:#e2e8f0; padding:0.15rem 0.5rem;
              border-radius:999px; font-size:0.8rem; margin-right:0.35rem; }}
    .badge.warn {{ background:#fef3c7; }}
    .badge.ok {{ background:#dcfce7; }}
    table {{ width:100%; border-collapse: collapse; background:#fff;
             border:1px solid #e2e8f0; border-radius:8px; overflow:hidden; }}
    th, td {{ text-align:left; padding:0.55rem 0.75rem; border-bottom:1px solid #e2e8f0;
              font-size:0.92rem; }}
    th {{ background:#f1f5f9; }}
    .actions {{ display:flex; gap:0.75rem; margin-top:1.25rem; flex-wrap:wrap; }}
    button {{ font-size:1rem; padding:0.65rem 1.1rem; border:none; border-radius:8px;
              cursor:pointer; font-weight:600; }}
    button.approve {{ background:#16a34a; color:#fff; }}
    button.escalate {{ background:#d97706; color:#fff; }}
    button.reject {{ background:#dc2626; color:#fff; }}
    button:disabled {{ opacity:0.5; cursor:not-allowed; }}
    .warn {{ color:#b45309; }}
    .note {{ margin-top:1rem; font-size:0.85rem; color:#64748b; }}
    #status {{ margin-top:1rem; font-weight:600; }}
    pre {{ background:#0f172a; color:#e2e8f0; padding:0.75rem; border-radius:8px;
           overflow:auto; font-size:0.75rem; max-height:220px; }}
  </style>
</head>
<body>
  <h1>HITL Claim Review Panel</h1>
  <p class="meta">
    <span class="badge ok">synthetic</span>
    <span class="badge warn">auto-approve OFF</span>
    <span class="badge">budget &lt;{view.operator_budget_s}s</span>
  </p>
  <p><strong>{html.escape(view.display_name)}</strong>
     ({html.escape(view.provider_id)}) · network
     <code>{html.escape(view.network_id)}</code></p>
  <p class="meta">Run <code>{html.escape(view.run_id)}</code></p>
  {missing}
  <table>
    <thead><tr><th>Claim</th><th>Value</th><th>Confidence</th><th>Evidence ref</th></tr></thead>
    <tbody>
      {''.join(claims_rows)}
    </tbody>
  </table>
  <div class="actions">
    <button class="approve" type="button" onclick="decide('approve')">Approve</button>
    <button class="escalate" type="button" onclick="decide('escalate')">Escalate</button>
    <button class="reject" type="button" onclick="decide('reject')">Reject</button>
  </div>
  <p class="note">
    Completion is blocked until you choose an action. Approve emits an F8 receipt;
    Escalate / Reject do not. Not a HITRUST or HIPAA-certified product claim.
  </p>
  <div id="status"></div>
  <details><summary>Panel JSON</summary><pre>{payload}</pre></details>
  <script>
    async function decide(action) {{
      const status = document.getElementById('status');
      status.textContent = 'Submitting ' + action + '…';
      document.querySelectorAll('button').forEach(b => b.disabled = true);
      try {{
        const res = await fetch('/decide', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{
            action: action,
            actor: 'hitl-web-panel',
            reason: 'web-panel:' + action
          }})
        }});
        const body = await res.json();
        if (!res.ok) throw new Error(body.error || res.statusText);
        status.textContent = 'Recorded: ' + body.action +
          (body.action === 'approve' ? ' → F8 receipt will emit' : ' → no receipt');
      }} catch (err) {{
        status.textContent = 'Error: ' + err;
        document.querySelectorAll('button').forEach(b => b.disabled = false);
      }}
    }}
  </script>
</body>
</html>
"""
