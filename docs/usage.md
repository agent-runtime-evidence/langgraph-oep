# Usage Notes

## What This Package Does

`langgraph-oep` wraps a LangGraph checkpointer and emits OEP `tool_permission_packet.v0` records when your graph explicitly marks a checkpoint as a permission decision.

It records evidence. It does not:

- call OPA
- enforce policy
- decide whether a tool call should run
- replace LangGraph checkpoints
- replace logs, traces, LangSmith, OTel, or your policy engine

## Policy Response

Pass the policy decision you already captured:

```python
policy_response = {
    "policy_ref": {
        "engine": "opa",
        "package": "data.my_agent.permissions",
        "policy_id": "tool-permission-policy",
        "policy_version": "0.1.0",
        "policy_uri": "permissions/tool_permissions.rego",
    },
    "decision": {
        "allow": True,
        "reason": "policy allowed this tool call",
        "matched_rule": "allow_tool_call",
        "opa_result_ref": "opa://decision/result",
    },
    "links": {
        "event_ref": "events/event.json",
        "release_manifest_ref": "manifest/release.json",
        "trace_ref": "traces/trace.json",
    },
}
```

For throwaway demos only, `DecisionContext(..., allow_placeholder_policy_response=True)` can create placeholder policy evidence. Do not use placeholder evidence for submission-readiness, incident review, audit, or production workflows.

## Decision Context Scope

Create a fresh `DecisionContext` for each graph execution scope. `DecisionContext` objects are single-use; the package raises `RuntimeError` if the same object is reused, nested, or shared concurrently so context-local evidence cannot leak across scopes.

## Marker Semantics

Set `OEP_EMIT_PERMISSION_CHANNEL` in the same state update as the tool/action/resource surface.

Accepted marker shapes:

```python
OEP_EMIT_PERMISSION_CHANNEL: True
OEP_EMIT_PERMISSION_CHANNEL: "tool_call_123"
OEP_EMIT_PERMISSION_CHANNEL: {"decision_key": "tool_call_123"}
```

Recommended: use a stable unique string or object key for every real decision.

Boolean markers are deduplicated by visible decision surface. That prevents duplicate records when LangGraph carries state forward, but it also means two identical visible decisions in the same wrapped saver can collapse into one record. Use explicit decision keys when in doubt.

## Sinks

Built-in sinks:

- `LocalJsonlSink(path, fsync=False)`
- `StdoutSink(pretty=False)`

Sinks are synchronous in v0.1.0. Async sink support is intentionally deferred.

`LocalJsonlSink` serializes writes inside one Python process. It is not a
cross-process file lock. If multiple workers or processes can emit records at
the same time, write to process-specific files or route packets through an
external collector.
