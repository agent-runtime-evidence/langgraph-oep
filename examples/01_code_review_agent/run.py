# ruff: noqa: E402, I001
from __future__ import annotations

from pathlib import Path
import sys
from typing import TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph_oep import (
    OEP_EMIT_PERMISSION_CHANNEL,
    Actor,
    DecisionContext,
    LocalJsonlSink,
    ModelBinding,
    attach_oep_writer,
)

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "oep-records.jsonl"
OUTPUT.unlink(missing_ok=True)


class State(TypedDict, total=False):
    tool: dict[str, object]
    requested_action: dict[str, object]
    resource: dict[str, object]
    oep_emit_permission: str
    output: str


def request_diff_inspection(state: State) -> State:
    del state
    return {
        "tool": {"name": "read_diff", "version": "0.1.0", "operation": "read"},
        "requested_action": {
            "action_type": "inspect_diff",
            "name": "inspect synthetic repository diff",
            "input_ref": "demo/fixtures/diff_synthetic_001.patch",
        },
        "resource": {
            "type": "repository_diff",
            "id": "diff_synthetic_001",
            "uri": "demo/fixtures/diff_synthetic_001.patch",
            "mutable": False,
        },
        OEP_EMIT_PERMISSION_CHANNEL: "tool_code_review_demo_0001",
        "output": "diff inspected: 12 lines changed, 0 risky patterns",
    }


builder = StateGraph(State)
builder.add_node("request_diff_inspection", request_diff_inspection)
builder.add_edge(START, "request_diff_inspection")
builder.add_edge("request_diff_inspection", END)
graph = builder.compile(checkpointer=MemorySaver())

attach_oep_writer(graph, sink=LocalJsonlSink(OUTPUT), on_error="raise")

with DecisionContext(
    actor=Actor(type="agent", id="agent_code_review_demo", display_name="code-review-agent-demo"),
    release_manifest_id="rmf_code_review_2026_06",
    policy_response={
        "policy_ref": {
            "engine": "opa",
            "package": "data.langgraph_oep.examples",
            "policy_id": "example-policy",
            "policy_version": "0.1.0",
            "policy_uri": "examples/policy/example.rego",
        },
        "decision": {
            "allow": True,
            "reason": "example policy allows this synthetic action",
            "matched_rule": "allow_example_action",
            "opa_result_ref": "opa://examples/result",
        },
        "links": {
            "event_ref": "examples/events/evt_code_review_demo_0001.json",
            "release_manifest_ref": "examples/manifests/rmf_code_review_2026_06.json",
            "trace_ref": "examples/traces/11111111111111111111111111111111.json",
        },
    },
    policy_bundle_version="sha256:" + "0" * 64,
    release_manifest_version="sha256:" + "1" * 64,
    model_binding=ModelBinding(
        alias="claude-sonnet-4-6",
        resolved_version="claude-sonnet-4-6-20260512",
        provider="anthropic",
    ),
    scoped_credential_lifetime="PT15M",
    packet_id="pder_code_review_demo_0001",
    event_id="evt_code_review_demo_0001",
    tool_call_id="tool_code_review_demo_0001",
    trace_id="11111111111111111111111111111111",
    span_id="2222222222222222",
    decision_time="2026-06-01T00:00:00Z",
):
    result = graph.invoke(
        {"output": "started"},
        config={"configurable": {"thread_id": "code-review-demo-001"}},
    )

print(result["output"])
print(f"OEP records written to {OUTPUT}")
