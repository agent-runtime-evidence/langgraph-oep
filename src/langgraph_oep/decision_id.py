"""Helpers for building the OEP v0.3 decision_id metadata object."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def build_decision_id(
    *,
    packet_id: str,
    tool_call_id: str,
    policy_bundle_version: str | None,
    decision_id_extras: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Build the v0.3 decision_id object with an auto-populated permission surface."""

    extras = dict(decision_id_extras or {})
    raw_permission = extras.get("permission")
    permission: dict[str, Any] = dict(raw_permission) if isinstance(raw_permission, Mapping) else {}

    permission["permission_packet_ref"] = packet_id
    permission["tool_call_id"] = tool_call_id
    if policy_bundle_version is not None:
        permission["policy_bundle_version"] = policy_bundle_version

    decision_id: dict[str, Any] = {
        "schema_version": "0.3",
        "permission": permission,
    }
    for surface in ("cost", "drift", "cache", "identity"):
        if surface in extras:
            decision_id[surface] = extras[surface]
    return decision_id
