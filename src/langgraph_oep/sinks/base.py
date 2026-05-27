"""Sink protocol for emitted OEP packets."""

from __future__ import annotations

from typing import Any, Protocol


class OEPSink(Protocol):
    """Minimal sink contract for OEP packet emission."""

    def write(self, packet: dict[str, Any]) -> None:
        """Persist or forward one OEP packet."""
