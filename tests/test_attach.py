from __future__ import annotations

import json
from typing import TypedDict

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from langgraph_oep import (
    OEP_EMIT_PERMISSION_CHANNEL,
    Actor,
    DecisionContext,
    LocalJsonlSink,
    OEPCheckpointSaver,
    attach_oep_writer,
)

from .helpers import FakeSaver, RecordingSink, sample_policy_response


class GraphStub:
    def __init__(self, checkpointer: FakeSaver | None) -> None:
        self.checkpointer = checkpointer


def test_attach_wraps_graph_checkpointer() -> None:
    graph = GraphStub(FakeSaver())
    sink = RecordingSink()

    result = attach_oep_writer(graph, sink=sink)

    assert result is graph
    assert isinstance(graph.checkpointer, OEPCheckpointSaver)


def test_attach_rejects_graph_without_checkpointer() -> None:
    with pytest.raises(ValueError, match="Graph has no checkpointer"):
        attach_oep_writer(GraphStub(None), sink=RecordingSink())


def test_attach_rejects_double_attach() -> None:
    graph = GraphStub(FakeSaver())
    attach_oep_writer(graph, sink=RecordingSink())

    with pytest.raises(ValueError, match="already has OEP"):
        attach_oep_writer(graph, sink=RecordingSink())


class DemoState(TypedDict, total=False):
    tool: dict[str, object]
    requested_action: dict[str, object]
    resource: dict[str, object]
    oep_emit_permission: bool
    output: str


def _request_permission(state: DemoState) -> DemoState:
    del state
    return {
        "tool": {"name": "read_diff", "version": "0.1.0", "operation": "read"},
        "requested_action": {
            "action_type": "inspect_diff",
            "name": "inspect diff",
            "input_ref": "diff.patch",
        },
        "resource": {
            "type": "repository_diff",
            "id": "diff_001",
            "uri": "diff.patch",
            "mutable": False,
        },
        OEP_EMIT_PERMISSION_CHANNEL: True,
    }


def _finish(state: DemoState) -> DemoState:
    del state
    return {"output": "ok"}


def test_attach_integration_with_langgraph_memory_saver(tmp_path) -> None:  # type: ignore[no-untyped-def]
    builder = StateGraph(DemoState)
    builder.add_node("request_permission", _request_permission)
    builder.add_node("finish", _finish)
    builder.add_edge(START, "request_permission")
    builder.add_edge("request_permission", "finish")
    builder.add_edge("finish", END)
    graph = builder.compile(checkpointer=MemorySaver())
    sink = LocalJsonlSink(tmp_path / "oep-records.jsonl")
    attach_oep_writer(graph, sink=sink, on_error="raise")

    with DecisionContext(
        actor=Actor(type="agent", id="agent_test", display_name="Agent Test"),
        release_manifest_id="rmf_test",
        policy_response=sample_policy_response(),
    ):
        result = graph.invoke({"output": "started"}, config={"configurable": {"thread_id": "t1"}})

    records = [json.loads(line) for line in sink.path.read_text(encoding="utf-8").splitlines()]
    assert result["output"] == "ok"
    assert len(records) == 1
    assert records[0]["tool"]["name"] == "read_diff"
