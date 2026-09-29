"""F1 synthetic fixture loader — SuperNode layout for HospitalCred / PayerEnrollment.

Path agreement (Leandro + Franco):
  fixtures/supernodes/HospitalCred/providers.json
  fixtures/supernodes/PayerEnrollment/providers.json
  fixtures/providers.json   # orchestrator aggregate (both slices)

Synthetic only. No live CAQH / NPDB / PHI.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional
import json

from poppy_orchestrator.contracts.claims import ClaimType

# F1 MVP typed claims (FLOWER-11). Extra F6 types (board_status, enrollment_status)
# may appear on SuperNode slices but are not required by F1 core.
F1_CORE_CLAIMS: frozenset[str] = frozenset(
    {
        ClaimType.LICENSE_ACTIVE.value,
        ClaimType.NPI_ENUMERATED.value,
        ClaimType.EXCLUSION_CLEAR.value,
        ClaimType.WORK_HISTORY_COMPLETE.value,
    }
)

FIXTURES_ROOT = Path(__file__).resolve().parents[2] / "fixtures"

SUPERNODE_LAYOUT: dict[str, Path] = {
    "HospitalCred": FIXTURES_ROOT / "supernodes" / "HospitalCred" / "providers.json",
    "PayerEnrollment": FIXTURES_ROOT / "supernodes" / "PayerEnrollment" / "providers.json",
    "Orchestrator": FIXTURES_ROOT / "providers.json",
}

HAPPY_PROVIDER_ID = "SYNTH-NPI-1999999999"
ESCALATE_PROVIDER_ID = "SYNTH-NPI-1888888888"


def _read_json(path: Path) -> dict[str, Any]:
    with path.open() as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"fixture root must be object: {path}")
    if data.get("meta", {}).get("synthetic") is not True:
        raise ValueError(f"fixture must declare meta.synthetic=true: {path}")
    return data


def load_hospital_cred_catalog(*, path: Optional[Path] = None) -> dict[str, Any]:
    return _read_json(path or SUPERNODE_LAYOUT["HospitalCred"])


def load_payer_enrollment_catalog(*, path: Optional[Path] = None) -> dict[str, Any]:
    return _read_json(path or SUPERNODE_LAYOUT["PayerEnrollment"])


def load_orchestrator_catalog(*, path: Optional[Path] = None) -> dict[str, Any]:
    return _read_json(path or SUPERNODE_LAYOUT["Orchestrator"])


def load_provider_row(
    provider_id: str,
    *,
    catalog: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Return one provider row from orchestrator catalog (both slices)."""
    data = catalog or load_orchestrator_catalog()
    for row in data.get("providers", []):
        if row.get("provider_id") == provider_id:
            return dict(row)
    raise KeyError(f"unknown synthetic provider: {provider_id}")


def providers_by_id(catalog: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {p["provider_id"]: p for p in catalog.get("providers", [])}


def f1_claims_present(provider_row: Mapping[str, Any]) -> set[str]:
    """Which of the four F1 core claims exist on this aggregate provider row."""
    found: set[str] = set()
    hospital = provider_row.get("hospital_cred") or {}
    payer = provider_row.get("payer_enrollment") or {}
    if "work_history_complete" in hospital:
        found.add("work_history_complete")
    for key in ("license_active", "npi_enumerated", "exclusion_clear"):
        if key in payer:
            found.add(key)
    return found
