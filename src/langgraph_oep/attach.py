"""Convenience API for attaching OEP emission to compiled LangGraph graphs."""

from __future__ import annotations

from typing import Any

from langgraph_oep.saver import OEPCheckpointSaver, OnError
from langgraph_oep.sinks.base import OEPSink


def attach_oep_writer(
    graph: Any,
    *,
    sink: OEPSink,
    on_error: OnError = "log",
) -> Any:
    """Wrap a compiled graph's checkpointer with OEPCheckpointSaver."""

    inner = getattr(graph, "checkpointer", None)
    if inner is None:
        raise ValueError(
            "Graph has no checkpointer. Compile with a checkpointer "
            "(MemorySaver, SqliteSaver, PostgresSaver, etc.) before attaching OEP writer."
        )
    if isinstance(inner, OEPCheckpointSaver):
        raise ValueError("Graph already has OEP writer attached.")
    graph.checkpointer = OEPCheckpointSaver(inner, sink, on_error=on_error)
    return graph
