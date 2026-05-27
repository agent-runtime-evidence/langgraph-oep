"""Identifier generation for OEP packets emitted from LangGraph checkpoints."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any


def generate_per_checkpoint_ids(checkpoint: Mapping[str, Any]) -> dict[str, str]:
    """Generate stable OEP identifiers from a LangGraph checkpoint id."""

    checkpoint_id = str(checkpoint["id"])
    checkpoint_hash = hashlib.sha256(checkpoint_id.encode("utf-8")).hexdigest()
    return {
        "packet_id": f"pder_lg_{checkpoint_hash[:24]}",
        "event_id": f"evt_lg_{checkpoint_hash[24:48]}",
        "tool_call_id": f"tool_lg_{checkpoint_hash[48:64]}",
        "span_id": checkpoint_hash[:16],
    }
