# langgraph-oep

[![PyPI version](https://img.shields.io/pypi/v/langgraph-oep.svg)](https://pypi.org/project/langgraph-oep/)
[![Python versions](https://img.shields.io/pypi/pyversions/langgraph-oep.svg)](https://pypi.org/project/langgraph-oep/)
[![CI](https://github.com/agent-runtime-evidence/langgraph-oep/actions/workflows/ci.yml/badge.svg)](https://github.com/agent-runtime-evidence/langgraph-oep/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

`langgraph-oep` records evidence about important LangGraph tool decisions.

Wrap your existing LangGraph checkpointer, mark the state update that represents a permission decision, and the wrapper writes an [Operational Evidence Plane (OEP)](https://github.com/agent-runtime-evidence/operational-evidence-plane) `tool_permission_packet.v0` JSONL record.

Use it when you need to answer questions like:

- Which policy version allowed this tool call?
- Which model alias and resolved model version were active?
- Which release manifest, trace, actor, cache entry, or scoped credential was bound to the decision?
- Would this old decision be worth replaying against a changed policy, model, cache, or credential surface?

This is an illustration-grade reference implementation: one inspectable wrapping pattern, not a production-certified observability platform.

## Install

```bash
pip install langgraph-oep
```

Requires Python 3.10+. CI covers LangGraph `0.2.x`, `0.3.x`, and `1.x`.

## When To Use It

Use `langgraph-oep` if you already use LangGraph checkpoints and want an append-only evidence record for selected tool permission decisions.

You probably do not need it if you only want normal LangGraph resume, time travel, local debugging, or ordinary application logs. LangGraph time travel and OEP-style evidence records solve different problems at different layers.

## 60-Second Example

This example writes one OEP packet to `./oep-records.jsonl`.

```python
from typing import TypedDict

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


class State(TypedDict, total=False):
    tool: dict
    requested_action: dict
    resource: dict
    oep_emit_permission: str
    output: str


def inspect_diff(state: State) -> State:
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
        "output": "diff inspected",
    }


builder = StateGraph(State)
builder.add_node("inspect_diff", inspect_diff)
builder.add_edge(START, "inspect_diff")
builder.add_edge("inspect_diff", END)
graph = builder.compile(checkpointer=MemorySaver())

attach_oep_writer(graph, sink=LocalJsonlSink("./oep-records.jsonl"))

with DecisionContext(
    actor=Actor(type="agent", id="agent_code_review", display_name="Code Review Agent"),
    release_manifest_id="rmf_code_review_2026_06",
    policy_response={
        "policy_ref": {
            "engine": "opa",
            "package": "data.code_review.permissions",
            "policy_id": "tool-permission-policy",
            "policy_version": "0.1.0",
            "policy_uri": "permissions/tool_permissions.rego",
        },
        "decision": {
            "allow": True,
            "reason": "policy allowed read-only diff inspection",
            "matched_rule": "allow_read_only_diff_inspection",
            "opa_result_ref": "opa://decision/code_review/001",
        },
        "links": {
            "event_ref": "events/code_review_001.json",
            "release_manifest_ref": "manifest/code_review_2026_06.json",
            "trace_ref": "traces/code_review_001.json",
        },
    },
    policy_bundle_version="sha256:" + "0" * 64,
    model_binding=ModelBinding(
        alias="claude-sonnet-4-6",
        resolved_version="claude-sonnet-4-6-20260512",
        provider="anthropic",
    ),
    scoped_credential_lifetime="PT15M",
):
    graph.invoke({"output": "started"}, config={"configurable": {"thread_id": "demo-thread"}})
```

The output is one JSON line. It includes fields like:

```json
{
  "schema_version": "oep.tool_permission_packet.v0",
  "tool_call_id": "tool_lg_...",
  "tool": {"name": "read_diff", "version": "0.1.0", "operation": "read"},
  "policy_bundle_version": "sha256:0000...",
  "model_alias": "claude-sonnet-4-6",
  "decision_id": {
    "schema_version": "0.3",
    "permission": {
      "permission_packet_ref": "pder_lg_...",
      "tool_call_id": "tool_lg_...",
      "policy_bundle_version": "sha256:0000..."
    }
  }
}
```

## How It Works

1. You keep your existing checkpointer (`MemorySaver`, SQLite, Postgres, or custom).
2. `attach_oep_writer(...)` wraps that checkpointer.
3. Your graph node writes `tool`, `requested_action`, `resource`, and `OEP_EMIT_PERMISSION_CHANNEL`.
4. `DecisionContext` supplies the evidence surfaces LangGraph does not know about: actor, release manifest, policy response, model binding, scoped credential lifetime, cache/cost/drift/identity extras.
5. On checkpoint write, the wrapper validates and writes an OEP packet to the sink.

`policy_response` is required by default. The package does not evaluate OPA or invent policy evidence; it records the policy result you pass in.

## Learn More

- [Quickstart details](docs/quickstart.md)
- [Policy response and marker semantics](docs/usage.md)
- [The 19 wrapper-injected fields](docs/19_wrapper_injected_fields.md)
- [Operational caveats](docs/operational_caveats.md)
- [Relationship to OEP](docs/relation_to_oep.md)

## Examples

Runnable examples live under `examples/`:

1. `01_code_review_agent` - single decision capture
2. `02_customer_support_with_credentials` - scoped credential lifetime
3. `03_rag_pipeline_with_cache` - cache identity
4. `04_multi_step_orchestration_with_policy` - repeated decisions under one policy bundle
5. `05_interrupt_resume_with_model_version` - approval capture and model-version drift

## Boundary

LangGraph's checkpoint design is correct for execution recovery and branched exploration. `langgraph-oep` records a separate evidence layer for selected decisions. No upstream approval or sponsorship is implied.

Treat emitted JSONL as sensitive operational evidence: records can include actor IDs, resource URIs, trace references, cache identifiers, policy refs, scoped credential metadata, and approval metadata.

## License

Apache 2.0.
