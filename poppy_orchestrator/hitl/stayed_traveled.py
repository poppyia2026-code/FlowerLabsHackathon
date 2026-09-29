"""F13 stayed-vs-traveled view — built from ClaimBundle / reply payloads in memory.

No new network calls. Reads ``privacy_summary`` attached to ClaimResponse
(plus the typed claims that traveled). Synthetic fixtures only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional
import html
import json

from poppy_orchestrator.contracts.claims import ClaimBundle, ClaimResponse
from poppy_orchestrator.contracts.privacy import PrivacySummary


@dataclass(frozen=True)
class NodeStayedTraveled:
    """One SuperNode column pair."""

    node_name: str
    ok: bool
    stayed_field_count: int
    stayed_preview: tuple[str, ...]
    traveled_claims: tuple[dict[str, Any], ...]
    count_line: str
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_name": self.node_name,
            "ok": self.ok,
            "stayed_field_count": self.stayed_field_count,
            "stayed_preview": list(self.stayed_preview),
            "traveled_claims": list(self.traveled_claims),
            "traveled_claim_count": len(self.traveled_claims),
            "count_line": self.count_line,
            "error": self.error,
        }


@dataclass(frozen=True)
class StayedTraveledView:
    """Side-by-side stayed vs traveled for HospitalCred + PayerEnrollment."""

    run_id: str
    provider_id: str
    display_name: str
    nodes: tuple[NodeStayedTraveled, ...]
    synthetic: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "provider_id": self.provider_id,
            "display_name": self.display_name,
            "synthetic": self.synthetic,
            "nodes": [n.to_dict() for n in self.nodes],
            "disclaimer": (
                "Synthetic fixtures only — no live CAQH/NPDB. "
                "Field paths stayed local; typed claims traveled. "
                "Not a HITRUST or HIPAA-certified product claim."
            ),
        }


def _count_line(stayed: int, traveled: int) -> str:
    claim_word = "typed claim" if traveled == 1 else "typed claims"
    return f"{stayed} fields stayed, {traveled} {claim_word} traveled"


def _node_from_response(
    node_name: str, response: Optional[ClaimResponse]
) -> NodeStayedTraveled:
    if response is None:
        return NodeStayedTraveled(
            node_name=node_name,
            ok=False,
            stayed_field_count=0,
            stayed_preview=(),
            traveled_claims=(),
            count_line=_count_line(0, 0),
            error="node missing from run",
        )
    summary: Optional[PrivacySummary] = response.privacy_summary
    claims = tuple(c.to_dict() for c in response.claims) if response.ok else ()
    if summary is not None:
        stayed_count = summary.stayed_field_count
        preview = summary.stayed_preview
        traveled_count = len(claims) if response.ok else summary.traveled_claim_count
    else:
        stayed_count = 0
        preview = ()
        traveled_count = len(claims)
    return NodeStayedTraveled(
        node_name=node_name,
        ok=bool(response.ok),
        stayed_field_count=stayed_count,
        stayed_preview=preview,
        traveled_claims=claims,
        count_line=_count_line(stayed_count, traveled_count),
        error=None if response.ok else (response.error or "ok=false"),
    )


def node_from_reply_dict(
    node_name: str, reply: Mapping[str, Any] | None
) -> NodeStayedTraveled:
    """Build a node view from a ClaimResponse-shaped dict already in a trace."""
    if not reply:
        return _node_from_response(node_name, None)
    from poppy_orchestrator.contracts.claims import claim_response_from_dict

    try:
        resp = claim_response_from_dict(dict(reply))
    except (KeyError, TypeError, ValueError) as exc:
        return NodeStayedTraveled(
            node_name=node_name,
            ok=False,
            stayed_field_count=0,
            stayed_preview=(),
            traveled_claims=(),
            count_line=_count_line(0, 0),
            error=f"unparseable reply: {exc}",
        )
    return _node_from_response(node_name, resp)


def build_stayed_traveled_view(bundle: ClaimBundle) -> StayedTraveledView:
    """Derive the F13 view from an in-memory ClaimBundle (no network)."""
    nodes = (
        _node_from_response("HospitalCred", bundle.hospital),
        _node_from_response("PayerEnrollment", bundle.payer),
    )
    return StayedTraveledView(
        run_id=bundle.run_id,
        provider_id=bundle.provider.provider_id,
        display_name=bundle.provider.display_name,
        nodes=nodes,
        synthetic=True,
    )


def build_stayed_traveled_from_trace(
    *,
    run_id: str,
    provider_id: str,
    display_name: str,
    hospital_reply: Mapping[str, Any] | None,
    payer_reply: Mapping[str, Any] | None,
) -> StayedTraveledView:
    """Same view from reply JSON already captured in a run/trace."""
    return StayedTraveledView(
        run_id=run_id,
        provider_id=provider_id,
        display_name=display_name,
        nodes=(
            node_from_reply_dict("HospitalCred", hospital_reply),
            node_from_reply_dict("PayerEnrollment", payer_reply),
        ),
        synthetic=True,
    )


def render_stayed_traveled_text(view: StayedTraveledView) -> str:
    lines = [
        "=== Stayed vs Traveled (F13) ===",
        f"Provider: {view.display_name} ({view.provider_id})",
        f"Run:      {view.run_id}",
        "Synthetic fixtures only — no live CAQH/NPDB.",
        "Raw dossier does not travel; typed claims do.",
        "",
    ]
    for node in view.nodes:
        lines.append(f"--- {node.node_name} ---")
        lines.append(f"  {node.count_line}")
        if node.error:
            lines.append(f"  ! {node.error}")
        lines.append("  Stayed (local field paths):")
        if not node.stayed_preview:
            lines.append("    (none)")
        else:
            for path in node.stayed_preview:
                lines.append(f"    · {path}")
        lines.append("  Traveled (typed claims):")
        if not node.traveled_claims:
            lines.append("    (none)")
        else:
            for claim in node.traveled_claims:
                lines.append(
                    f"    · {claim.get('claim_type')} = {claim.get('value')!r}"
                )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_stayed_traveled_sections(view: StayedTraveledView) -> str:
    """Inner sections only — safe to embed inside the F7 HITL panel HTML."""
    sections: list[str] = []
    for node in view.nodes:
        stayed_items = "".join(
            f"<li><code>{html.escape(p)}</code></li>" for p in node.stayed_preview
        ) or "<li><em>(none)</em></li>"
        traveled_rows = []
        for claim in node.traveled_claims:
            traveled_rows.append(
                "<tr>"
                f"<td>{html.escape(str(claim.get('claim_type')))}</td>"
                f"<td><code>{html.escape(repr(claim.get('value')))}</code></td>"
                f"<td>{html.escape(str(claim.get('confidence', '')))}</td>"
                "</tr>"
            )
        if not traveled_rows:
            traveled_rows.append(
                '<tr><td colspan="3"><em>No claims traveled</em></td></tr>'
            )
        err = (
            f"<p class='warn'>{html.escape(node.error)}</p>" if node.error else ""
        )
        sections.append(
            f"""
    <section class="node f13-node">
      <h2>{html.escape(node.node_name)}</h2>
      <p class="count"><strong>{html.escape(node.count_line)}</strong></p>
      {err}
      <div class="cols f13-cols">
        <div class="col stayed">
          <h3>Stayed at node</h3>
          <p class="sub">{html.escape(str(node.stayed_field_count))} leaf fields
             — inventory only (values never egressed)</p>
          <ul class="paths">{stayed_items}</ul>
        </div>
        <div class="col traveled">
          <h3>Traveled (typed claims)</h3>
          <p class="sub">{len(node.traveled_claims)} claim(s) in reply payload</p>
          <table>
            <thead><tr><th>Claim</th><th>Value</th><th>Confidence</th></tr></thead>
            <tbody>{''.join(traveled_rows)}</tbody>
          </table>
        </div>
      </div>
    </section>
"""
        )
    return "".join(sections)


def render_stayed_traveled_html(view: StayedTraveledView) -> str:
    """Self-contained screenshotable HTML for judges / G3 kit."""
    sections_html = render_stayed_traveled_sections(view)
    payload = html.escape(json.dumps(view.to_dict(), indent=2))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>PrivCred Stayed vs Traveled (F13)</title>
  <style>
    :root {{ font-family: ui-sans-serif, system-ui, sans-serif; color: #0f172a; }}
    body {{ max-width: 1100px; margin: 1.5rem auto; padding: 0 1rem; background: #f8fafc; }}
    h1 {{ font-size: 1.4rem; margin-bottom: 0.25rem; }}
    .meta {{ color: #475569; font-size: 0.95rem; }}
    .badge {{ display:inline-block; background:#e2e8f0; padding:0.15rem 0.5rem;
              border-radius:999px; font-size:0.8rem; margin-right:0.35rem; }}
    .badge.ok {{ background:#dcfce7; }}
    .node {{ background:#fff; border:1px solid #e2e8f0; border-radius:10px;
             padding:1rem 1.1rem; margin:1.25rem 0; }}
    .node h2 {{ margin:0 0 0.35rem; font-size:1.15rem; }}
    .count {{ color:#0f766e; margin:0.25rem 0 0.75rem; }}
    .cols {{ display:grid; grid-template-columns:1fr 1fr; gap:1rem; }}
    @media (max-width: 800px) {{ .cols {{ grid-template-columns:1fr; }} }}
    .col {{ border:1px solid #e2e8f0; border-radius:8px; padding:0.75rem; background:#f8fafc; }}
    .col.stayed {{ border-left:4px solid #64748b; }}
    .col.traveled {{ border-left:4px solid #0ea5e9; }}
    .col h3 {{ margin:0 0 0.35rem; font-size:1rem; }}
    .sub {{ font-size:0.8rem; color:#64748b; margin:0 0 0.5rem; }}
    ul.paths {{ max-height:280px; overflow:auto; margin:0; padding-left:1.1rem;
                font-size:0.82rem; }}
    table {{ width:100%; border-collapse:collapse; background:#fff; font-size:0.88rem; }}
    th, td {{ text-align:left; padding:0.4rem 0.55rem; border-bottom:1px solid #e2e8f0; }}
    th {{ background:#f1f5f9; }}
    .warn {{ color:#b45309; }}
    .note {{ font-size:0.85rem; color:#64748b; margin-top:1rem; }}
    pre {{ background:#0f172a; color:#e2e8f0; padding:0.75rem; border-radius:8px;
           overflow:auto; font-size:0.72rem; max-height:260px; }}
  </style>
</head>
<body>
  <h1>Stayed vs Traveled</h1>
  <p class="meta">
    <span class="badge ok">synthetic</span>
    <span class="badge">F13 / FLOWER-34</span>
  </p>
  <p><strong>{html.escape(view.display_name)}</strong>
     (<code>{html.escape(view.provider_id)}</code>)</p>
  <p class="meta">Run <code>{html.escape(view.run_id)}</code></p>
  {sections_html}
  <p class="note">
    Built from ClaimResponse privacy_summary already on the run — no extra network calls.
    Not a HITRUST or HIPAA-certified product claim. No live CAQH/NPDB.
  </p>
  <details><summary>View JSON</summary><pre>{payload}</pre></details>
</body>
</html>
"""


def attach_stayed_traveled_to_panel_dict(
    panel: dict[str, Any], view: StayedTraveledView
) -> dict[str, Any]:
    """Embed F13 block into an existing panel dict (HITL JSON)."""
    out = dict(panel)
    out["stayed_vs_traveled"] = view.to_dict()
    return out
