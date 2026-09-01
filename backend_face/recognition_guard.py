"""Dependency-free identity state guard for the live face pipeline.

This module intentionally imports only the Python standard library so CI can
exercise identity-switch behaviour without installing OpenCV/NumPy/InsightFace.
"""

from __future__ import annotations

import re
from typing import Any, MutableMapping

UNKNOWN = "Unknown"
_SAFE_KEY_RE = re.compile(r"[^a-z0-9_.-]+")


def normalize_identity(name: Any) -> str:
    value = str(name or "").strip()
    if not value or value.lower() == "unknown":
        return UNKNOWN
    return value


def stable_known_evidence_key(name: Any) -> str:
    """Return a camera-stable evidence key that never contains a tracker id."""
    value = normalize_identity(name)
    if value == UNKNOWN:
        return "unknown"
    slug = _SAFE_KEY_RE.sub("_", value.lower()).strip("_") or "known"
    return f"known:{slug}"


def update_identity_state(
    state: MutableMapping[str, Any],
    candidate_name: Any,
    *,
    candidate_is_strong: bool,
    confirm_hits: int = 2,
    switch_hits: int = 4,
) -> str:
    """Apply conservative temporal confirmation to one tracker state.

    Rules:
    * A new known identity is not exposed until it agrees for ``confirm_hits``
      fresh recognition attempts.
    * A confirmed identity can never silently become a different identity.
      Conflicting evidence immediately exposes ``Unknown`` while a separate
      ``switch_hits`` confirmation streak is collected.
    * Weak/unknown evidence never promotes an identity and never completes a
      pending identity switch.
    * Seeing the already-confirmed identity again clears a conflict.
    """
    confirm_hits = max(1, int(confirm_hits))
    switch_hits = max(confirm_hits + 1, int(switch_hits))

    candidate = normalize_identity(candidate_name)
    confirmed = normalize_identity(state.get("confirmed_name"))
    pending = normalize_identity(state.get("pending_name"))
    pending_hits = max(0, int(state.get("pending_hits", 0) or 0))
    conflict = bool(state.get("identity_conflict", False))

    if not candidate_is_strong or candidate == UNKNOWN:
        # Do not allow uncertain evidence to progress a new identity or switch.
        if confirmed == UNKNOWN:
            state["pending_name"] = None
            state["pending_hits"] = 0
            state["identity_conflict"] = False
            state["confirmed_name"] = UNKNOWN
            return UNKNOWN
        # Once a conflicting identity has been observed, remain Unknown until
        # the original identity is freshly re-confirmed or the switch completes.
        return UNKNOWN if conflict else confirmed

    if confirmed == UNKNOWN:
        if pending == candidate:
            pending_hits += 1
        else:
            pending = candidate
            pending_hits = 1
        state["pending_name"] = pending
        state["pending_hits"] = pending_hits
        state["identity_conflict"] = False
        if pending_hits >= confirm_hits:
            state["confirmed_name"] = candidate
            state["pending_name"] = None
            state["pending_hits"] = 0
            return candidate
        state["confirmed_name"] = UNKNOWN
        return UNKNOWN

    if candidate == confirmed:
        state["confirmed_name"] = confirmed
        state["pending_name"] = None
        state["pending_hits"] = 0
        state["identity_conflict"] = False
        return confirmed

    # Fresh strong evidence says this track may now be somebody else. Never
    # expose the new label until a longer independent confirmation streak wins.
    state["identity_conflict"] = True
    if pending == candidate:
        pending_hits += 1
    else:
        pending = candidate
        pending_hits = 1
    state["pending_name"] = pending
    state["pending_hits"] = pending_hits

    if pending_hits >= switch_hits:
        state["confirmed_name"] = candidate
        state["pending_name"] = None
        state["pending_hits"] = 0
        state["identity_conflict"] = False
        return candidate

    return UNKNOWN
