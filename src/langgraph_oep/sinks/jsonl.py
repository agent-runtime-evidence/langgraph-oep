"""Local JSON Lines sink for OEP packets."""

from __future__ import annotations

import json
import os
from pathlib import Path
from threading import Lock
from typing import Any


class LocalJsonlSink:
    """Append OEP packets to a local JSON Lines file.

    Writes are serialized within one Python process. Use separate files or an
    external collector when multiple processes may emit records concurrently.
    """

    def __init__(self, path: str | Path, *, fsync: bool = False) -> None:
        candidate = Path(path)
        self._path = candidate / "oep.jsonl" if candidate.suffix == "" else candidate
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._fsync = fsync
        self._lock = Lock()

    @property
    def path(self) -> Path:
        return self._path

    def write(self, packet: dict[str, Any]) -> None:
        line = json.dumps(packet, sort_keys=True, ensure_ascii=False) + "\n"
        with self._lock, self._path.open("a", encoding="utf-8") as handle:
            handle.write(line)
            if self._fsync:
                handle.flush()
                os.fsync(handle.fileno())
