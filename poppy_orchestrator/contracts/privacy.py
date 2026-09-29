"""F13 stayed-vs-traveled privacy helpers (synthetic only).

Counts leaf fields in a SuperNode ``local_record`` and builds a
``PrivacySummary`` that travels with ClaimResponse — field *paths* and
counts only. Raw dossier values never become the traveled payload.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


def leaf_field_paths(obj: Any, prefix: str = "") -> list[str]:
    """Return dotted/indexed paths for every scalar leaf under ``obj``."""
    out: list[str] = []
    if isinstance(obj, Mapping):
        for key, value in obj.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            out.extend(leaf_field_paths(value, path))
    elif isinstance(obj, (list, tuple)):
        for index, value in enumerate(obj):
            path = f"{prefix}[{index}]"
            out.extend(leaf_field_paths(value, path))
    else:
        if prefix:
            out.append(prefix)
    return out


def count_leaf_fields(obj: Any) -> int:
    return len(leaf_field_paths(obj))


@dataclass(frozen=True)
class PrivacySummary:
    """Metadata proving what stayed local vs what typed claims traveled."""

    stayed_field_count: int
    stayed_preview: tuple[str, ...]
    traveled_claim_count: int

    def count_line(self) -> str:
        claims = self.traveled_claim_count
        claim_word = "typed claim" if claims == 1 else "typed claims"
        return (
            f"{self.stayed_field_count} fields stayed, "
            f"{claims} {claim_word} traveled"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "stayed_field_count": self.stayed_field_count,
            "stayed_preview": list(self.stayed_preview),
            "traveled_claim_count": self.traveled_claim_count,
        }


def privacy_summary_from_local_record(
    local_record: Mapping[str, Any] | None,
    *,
    traveled_claim_count: int,
) -> PrivacySummary | None:
    """Build summary from a synthetic local_record (or None if absent)."""
    if not local_record:
        return None
    paths = leaf_field_paths(local_record)
    return PrivacySummary(
        stayed_field_count=len(paths),
        stayed_preview=tuple(paths),
        traveled_claim_count=int(traveled_claim_count),
    )


def privacy_summary_from_dict(data: Mapping[str, Any]) -> PrivacySummary:
    preview = data.get("stayed_preview") or ()
    return PrivacySummary(
        stayed_field_count=int(data["stayed_field_count"]),
        stayed_preview=tuple(str(p) for p in preview),
        traveled_claim_count=int(data["traveled_claim_count"]),
    )
