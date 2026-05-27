"""Stdout sink for debugging emitted OEP packets."""

from __future__ import annotations

import json
import sys
from typing import Any, TextIO


class StdoutSink:
    """Write packets to stdout as compact or pretty JSON."""

    def __init__(self, *, pretty: bool = False, stream: TextIO | None = None) -> None:
        self._pretty = pretty
        self._stream = stream

    def write(self, packet: dict[str, Any]) -> None:
        stream = self._stream or sys.stdout
        if self._pretty:
            stream.write(json.dumps(packet, indent=2, sort_keys=True, ensure_ascii=False))
            stream.write("\n")
            return
        stream.write(json.dumps(packet, sort_keys=True, ensure_ascii=False))
        stream.write("\n")
