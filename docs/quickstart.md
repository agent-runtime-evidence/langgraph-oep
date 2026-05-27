# Quickstart Details

The README shows a full copy-paste example. This page explains the moving parts.

## 1. Compile With Your Normal Checkpointer

`langgraph-oep` wraps an existing LangGraph checkpointer. It does not replace your persistence backend.

```python
graph = builder.compile(checkpointer=MemorySaver())
attach_oep_writer(graph, sink=LocalJsonlSink("./oep-records.jsonl"))
```

## 2. Mark The State Update To Record

The wrapper emits only when the checkpoint state includes:

- `tool`
- `requested_action`
- `resource`
- `OEP_EMIT_PERMISSION_CHANNEL`

Recommended marker usage:

```python
return {
    "tool": {"name": "read_diff", "version": "0.1.0", "operation": "read"},
    "requested_action": {
        "action_type": "inspect_diff",
        "name": "inspect repository diff",
        "input_ref": "diffs/001.patch",
    },
    "resource": {
        "type": "repository_diff",
        "id": "diff_001",
        "uri": "diffs/001.patch",
        "mutable": False,
    },
    OEP_EMIT_PERMISSION_CHANNEL: "tool_read_diff_001",
}
```

Use a stable unique string for each real decision. Boolean `True` works for demos, but string keys are safer when the same action can happen more than once in a run.

## 3. Pass Runtime Evidence In DecisionContext

`DecisionContext` supplies fields that LangGraph does not natively bind to a checkpoint:

- actor identity
- release manifest id/version
- policy response and policy bundle version
- model alias/resolved version/provider
- scoped credential lifetime
- approval capture
- optional cache/cost/drift/identity surfaces

`policy_response` is required by default. The wrapper records policy evidence; it does not evaluate policy for you.

## 4. Read The JSONL

Each emitted packet is one line in the sink file. You can inspect it with:

```bash
python -m json.tool < oep-records.jsonl
```

For production-style pipelines, treat the file as sensitive operational evidence and forward it to your normal secure log or evidence store.
