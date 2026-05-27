from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict

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


class ExampleState(TypedDict, total=False):
    tool: dict[str, Any]
    requested_action: dict[str, Any]
    resource: dict[str, Any]
    oep_emit_permission: bool
    output: str


def example_policy_response(
    *,
    event_id: str,
    release_manifest_id: str,
    trace_id: str,
) -> dict[str, Any]:
    return {
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
            "event_ref": f"examples/events/{event_id}.json",
            "release_manifest_ref": f"examples/manifests/{release_manifest_id}.json",
            "trace_ref": f"examples/traces/{trace_id}.json",
        },
    }


def run_single_decision(
    *,
    output_path: Path,
    thread_id: str,
    actor: Actor,
    release_manifest_id: str,
    tool: dict[str, Any],
    requested_action: dict[str, Any],
    resource: dict[str, Any],
    result_text: str,
    packet_id: str,
    event_id: str,
    tool_call_id: str,
    trace_id: str,
    span_id: str,
    decision_time: str,
    policy_bundle_version: str,
    release_manifest_version: str | None = None,
    model_binding: ModelBinding | None = None,
    scoped_credential_lifetime: str | None = None,
    approval_capture: dict[str, Any] | None = None,
    decision_id_extras: dict[str, Any] | None = None,
    policy_response: dict[str, Any] | None = None,
    reset_output: bool = True,
) -> ExampleState:
    if reset_output:
        output_path.unlink(missing_ok=True)

    def capture_decision(state: ExampleState) -> ExampleState:
        del state
        return {
            "tool": tool,
            "requested_action": requested_action,
            "resource": resource,
            OEP_EMIT_PERMISSION_CHANNEL: True,
            "output": result_text,
        }

    builder = StateGraph(ExampleState)
    builder.add_node("capture_decision", capture_decision)
    builder.add_edge(START, "capture_decision")
    builder.add_edge("capture_decision", END)
    graph = builder.compile(checkpointer=MemorySaver())
    attach_oep_writer(graph, sink=LocalJsonlSink(output_path), on_error="raise")

    with DecisionContext(
        actor=actor,
        release_manifest_id=release_manifest_id,
        policy_bundle_version=policy_bundle_version,
        release_manifest_version=release_manifest_version,
        model_binding=model_binding or ModelBinding(),
        scoped_credential_lifetime=scoped_credential_lifetime,
        approval_capture=approval_capture,
        policy_response=policy_response
        or example_policy_response(
            event_id=event_id,
            release_manifest_id=release_manifest_id,
            trace_id=trace_id,
        ),
        trace_id=trace_id,
        decision_id_extras=decision_id_extras,
        packet_id=packet_id,
        event_id=event_id,
        tool_call_id=tool_call_id,
        span_id=span_id,
        decision_time=decision_time,
    ):
        return graph.invoke({"output": "started"}, config={"configurable": {"thread_id": thread_id}})
