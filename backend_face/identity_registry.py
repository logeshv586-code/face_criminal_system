"""Dependency-free helpers for deciding which gallery identities are registered.

Live recognition may still have embeddings or tracker state in memory for a short
period after a registration record changes.  These helpers make metadata the
source of truth for whether an identity is currently allowed to be named.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional, Set


def _norm(value: Any) -> str:
    return str(value or "").strip().casefold()


def registered_identity_keys(metadata: Any, company_id: Optional[str] = None) -> Set[str]:
    """Return normalized person IDs registered for one company.

    Supports both metadata layouts used by the project:
    ``{"persons": {person_id: {...}}}`` and the legacy flat
    ``{person_id: {...}}`` structure.
    """
    if not isinstance(metadata, Mapping):
        return set()

    nested = metadata.get("persons")
    persons = nested if isinstance(nested, Mapping) else metadata
    target_company = _norm(company_id or "default")
    result: Set[str] = set()

    for person_id, details in persons.items():
        if person_id in {"persons", "last_updated", "total_registered"}:
            continue
        if not isinstance(details, Mapping):
            continue
        # Registration rows always contain a name.  Requiring it avoids treating
        # unrelated metadata dictionaries as biometric identities.
        if not str(details.get("name") or "").strip():
            continue
        row_company = _norm(details.get("company_id") or "default")
        if row_company == target_company:
            key = _norm(person_id)
            if key:
                result.add(key)

    return result


def identity_is_registered(name: Any, registered_keys: Optional[Set[str]]) -> bool:
    """Fail open only when metadata is unavailable (``None``).

    An empty set means metadata was available and the company currently has no
    registered identities, so no known label is allowed.
    """
    if registered_keys is None:
        return True
    return _norm(name) in registered_keys
