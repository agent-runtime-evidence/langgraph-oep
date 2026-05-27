# Walkthrough: From LangGraph time travel to substitution-class replay

This walkthrough takes one realistic scenario — a LangGraph code-review agent that touched
a repository diff — through a production reconstruction question, shows what LangGraph's
own time travel gives you, where the persistence model stops, and what the
`langgraph-oep` wrapper adds. It uses the runnable [`examples/01_code_review_agent`](../examples/01_code_review_agent) as
its substrate and quotes LangGraph's own documentation for the boundary claims. No
production data; the scenario is synthetic by design.

If you want the 60-second copy-paste, read [the README](../README.md). This page is for the
case where you want to understand which problem the wrapper actually addresses, what it
deliberately does not address, and how it differs from LangGraph's built-in time travel.

---

## 1. The question this walkthrough is built around

A week from now, an incident lands.

> "Our code-review agent approved a change last Wednesday that we now think it should have
> blocked. Walk me through what the agent saw at decision time. Which policy bundle was
> active? Which resolved model version actually ran? Which cache entry shaped the diff
> summary it consumed? Was that scoped credential still valid?"

The question is not "what was the agent's state in step 3 of run 47" — LangGraph's
checkpoint model already answers that very well. The question is "what surfaces did the
agent's decision **bind to** at the moment of decision, and how would the outcome have
changed if any of them had been different?"

These are two different replay primitives. Both are legitimate. They sit at different
layers. This walkthrough is about the seam.

---

## 2. The scenario — one node, one decision

The agent does one thing: inspect a synthetic repository diff and emit a single
permission-bearing action. The full runnable code is in
[`examples/01_code_review_agent/run.py`](../examples/01_code_review_agent/run.py). The
essence is below.

```python
class State(TypedDict, total=False):
    tool: dict[str, object]
    requested_action: dict[str, object]
    resource: dict[str, object]
    oep_emit_permission: str
    output: str


def request_diff_inspection(state: State) -> State:
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
        "output": "diff inspected: 12 lines changed, 0 risky patterns",
    }


builder = StateGraph(State)
builder.add_node("request_diff_inspection", request_diff_inspection)
builder.add_edge(START, "request_diff_inspection")
builder.add_edge("request_diff_inspection", END)
graph = builder.compile(checkpointer=MemorySaver())
```

One node, one decision, one checkpointer. A toy on purpose. The reconstruction question
is still real.

---

## 3. What LangGraph time travel gives you

LangGraph's persistence model is built around `StateSnapshot`. The official LangGraph
documentation describes the checkpoint metadata captured at each super-step:

| `StateSnapshot` field | What it captures |
|---|---|
| `values` | State channel values at this checkpoint |
| `next` | Which nodes execute next from this checkpoint |
| `metadata` | Execution source, node outputs, step counter |
| `created_at` | Timestamp of the checkpoint write |
| `parent_config` | Reference to the previous checkpoint in the thread |

You can reach any prior step with `graph.get_state_history(config)` and re-execute from
it. This is what LangGraph calls **time travel**. From the LangGraph time-travel docs:

> "Replay re-executes nodes — it doesn't just read from cache. LLM calls, API requests,
> and interrupts fire again and may return different results."

And from the persistence docs:

> "Nodes after the checkpoint re-execute, including any LLM calls, API requests, or
> interrupts — which are always re-triggered during replay."

That is exactly the right primitive for what it is designed to do:

- recover from a failed run when external systems are still reachable
- explore an alternative branch from a checkpoint with a modified state value
- test a different prompt or different tool sequence against the same starting point
- A/B explore alternative agent paths during development

The world will return slightly different LLM and API responses each time you replay,
because the inputs may be the same but the downstream services are not pinned. That is
fine for development workflow and state recovery. It is not the answer to last week's
incident.

---

## 4. What the StateSnapshot does not bind natively

The reconstruction question from §1 asks about surfaces the agent's decision **bound to**
at decision time:

- which **model alias** the agent called, and which **resolved model version** that alias
  resolved to on that exact day
- which **policy bundle version** evaluated the permission for this tool call
- which **release manifest version** the agent was running under
- which **scoped credential lifetime** was active for the resource
- which **actor** identity made the request, with display-name resolution at decision time
- whether an **approval capture** happened, and if so under what conditions
- where the **trace** and **event** records live for join purposes

`StateSnapshot` was not designed to bind those surfaces to the checkpoint. It does not
need to: its job is execution recovery and branched exploration. Those surfaces sit in
your release manifest, your policy engine, your model client, your secrets manager,
your trace pipeline. Each is correct in its own home. None of them are pinned to a
checkpoint by `values / next / metadata / created_at / parent_config`.

If your reconstruction needs them joined under one decision identifier — for example
to answer "would this decision have been different under the new policy bundle that
shipped on Friday?" — the join discipline has to come from somewhere else.

---

## 5. Adding `langgraph-oep` — the diff

`langgraph-oep` wraps an existing LangGraph checkpointer and writes a separate evidence
record when your graph explicitly marks a checkpoint as a permission decision. The
diff against the §2 code is small.

```python
from langgraph_oep import (
    OEP_EMIT_PERMISSION_CHANNEL,
    Actor,
    DecisionContext,
    LocalJsonlSink,
    ModelBinding,
    attach_oep_writer,
)


def request_diff_inspection(state: State) -> State:
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
        OEP_EMIT_PERMISSION_CHANNEL: "tool_code_review_demo_0001",  # <-- added
        "output": "diff inspected: 12 lines changed, 0 risky patterns",
    }


graph = builder.compile(checkpointer=MemorySaver())
attach_oep_writer(graph, sink=LocalJsonlSink("./oep-records.jsonl"))  # <-- added

with DecisionContext(                                                # <-- added
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
        "decision": {"allow": True, "reason": "example policy allows this synthetic action",
                     "matched_rule": "allow_example_action", "opa_result_ref": "opa://examples/result"},
        "links": {"event_ref": "examples/events/evt_code_review_demo_0001.json",
                  "release_manifest_ref": "examples/manifests/rmf_code_review_2026_06.json",
                  "trace_ref": "examples/traces/11111111111111111111111111111111.json"},
    },
    policy_bundle_version="sha256:" + "0" * 64,
    release_manifest_version="sha256:" + "1" * 64,
    model_binding=ModelBinding(alias="claude-sonnet-4-6",
                               resolved_version="claude-sonnet-4-6-20260512",
                               provider="anthropic"),
    scoped_credential_lifetime="PT15M",
):
    graph.invoke({"output": "started"}, config={"configurable": {"thread_id": "code-review-demo-001"}})
```

Three additions:

1. `OEP_EMIT_PERMISSION_CHANNEL: "tool_code_review_demo_0001"` inside the node return,
   marking this checkpoint as the permission decision. The string is a stable unique
   key for this exact decision; boolean markers work for demos but a string is safer
   when the same shape of action can happen more than once.
2. `attach_oep_writer(graph, sink=LocalJsonlSink(...))` wraps the inner checkpointer.
   The graph keeps its `MemorySaver`; the wrapper sits in front of it.
3. `with DecisionContext(...)` carries the runtime evidence LangGraph does not natively
   bind: actor identity, release manifest, policy response, model binding, scoped
   credential lifetime, optional cache / cost / drift / identity surfaces. The wrapper
   does **not** evaluate policy — it records the policy result you already captured
   from your own engine.

Compile, run, and the wrapper writes one JSONL line per marked permission decision.

---

## 6. What the packet records

A single run of the example above writes one line to `oep-records.jsonl`. Re-formatted
for reading, it looks like this:

```json
{
  "schema_version": "oep.tool_permission_packet.v0",
  "tool_call_id": "tool_code_review_demo_0001",
  "tool": { "name": "read_diff", "operation": "read", "version": "0.1.0" },
  "requested_action": {
    "action_type": "inspect_diff",
    "input_ref": "demo/fixtures/diff_synthetic_001.patch",
    "name": "inspect synthetic repository diff"
  },
  "resource": { "id": "diff_synthetic_001", "mutable": false, "type": "repository_diff",
                "uri": "demo/fixtures/diff_synthetic_001.patch" },
  "actor": { "type": "agent", "id": "agent_code_review_demo",
             "display_name": "code-review-agent-demo" },
  "policy": { "engine": "opa", "package": "data.langgraph_oep.examples",
              "policy_id": "example-policy", "policy_uri": "examples/policy/example.rego",
              "policy_version": "0.1.0" },
  "decision": { "allow": true, "matched_rule": "allow_example_action",
                "opa_result_ref": "opa://examples/result",
                "reason": "example policy allows this synthetic action" },
  "policy_bundle_version": "sha256:0000...",
  "release_manifest_id": "rmf_code_review_2026_06",
  "release_manifest_version": "sha256:1111...",
  "model_alias": "claude-sonnet-4-6",
  "resolved_model_version": "claude-sonnet-4-6-20260512",
  "model_provider": "anthropic",
  "scoped_credential_lifetime": "PT15M",
  "approval_capture": null,
  "links": { "event_ref": "examples/events/evt_code_review_demo_0001.json",
             "release_manifest_ref": "examples/manifests/rmf_code_review_2026_06.json",
             "trace_ref": "examples/traces/11111111111111111111111111111111.json" },
  "decision_id": {
    "schema_version": "0.3",
    "permission": {
      "permission_packet_ref": "pder_code_review_demo_0001",
      "policy_bundle_version": "sha256:0000...",
      "tool_call_id": "tool_code_review_demo_0001"
    }
  },
  "claim_boundary": "Illustration-grade record; not a compliance, audit, or model-quality claim."
}
```

The full live example output lives in
[`examples/01_code_review_agent/expected_output.jsonl`](../examples/01_code_review_agent/expected_output.jsonl).
Nineteen of the visible fields are injected by the wrapper from `DecisionContext` and
session state — the field map is documented in
[`docs/19_wrapper_injected_fields.md`](19_wrapper_injected_fields.md). The remaining
tool / requested_action / resource fields are projected from the state channel values
the node returned.

The single load-bearing field is `decision_id`. It binds the tool call id, the policy
bundle version, and the permission packet reference into one stable identifier. That
identifier is the join key when a reconstruction question lands.

`claim_boundary` is emitted as required schema context. It is not a marketing claim. It
is a literal statement that this record is illustration-grade — placeholder policy
responses, demo identifiers, synthetic credential lifetime. Treat the JSONL output as
sensitive operational evidence whenever the inputs are real.

---

## 7. Substitution-class replay across stored surfaces

Time travel from §3 re-executes the same nodes with the same inputs and accepts that
downstream services may return different results each time. That is one replay
primitive.

The other primitive — call it **counterfactual** or **substitution-class** — answers a
different question. Given the recorded packet from §6, you can ask:

- **Substitute the policy bundle.** "Replay this decision against the policy bundle that
  shipped on Friday. Would `decision.allow` have come out the same?" The packet records
  `policy_bundle_version` and the policy `package` / `policy_id` / `policy_uri`. With
  those, a separate replay tool can re-evaluate the recorded `requested_action` and
  `resource` against the new bundle and report the diff.
- **Substitute the model version.** "Replay this decision under `claude-sonnet-4-6-20260520`
  instead of `claude-sonnet-4-6-20260512`. Did the alias resolution drift between the two
  recorded resolved versions matter for this class of decisions?" The packet binds
  `model_alias` and `resolved_model_version` separately, which is the point — the alias
  is what your code asked for, the resolved version is what actually ran.
- **Substitute the cache state.** "Replay this decision against a cache that has been
  cleared of the entry the agent consumed last Wednesday." Cache identity is one of the
  optional `DecisionContext` extras the wrapper records when supplied; the packet then
  carries the cache surface alongside the rest.

The wrapper does not perform these substitutions itself. v0.1.0 records the evidence; the
substitution-class replay engine lives upstream in
[Operational Evidence Plane](https://github.com/agent-runtime-evidence/operational-evidence-plane)
v0.3.0, where the counterfactual replay primitives (CR-002 / CR-003 / CR-004) operate on
records with this exact schema. The wrapper's job is to make sure the recorded surfaces
are precise enough to be substitutable later.

I describe the broader replay primitive in my arXiv preprint on the operational
evidence plane (paper27, `arXiv:2605.12078`). The walkthrough version here is the
small, inspectable adapter that connects a LangGraph deployment to that record schema.

---

## 8. Honest accounting

This is one inspectable wrapping pattern. It is not a production-certified observability
platform and it does not claim to be.

What the v0.1.0 wrapper does:

- writes one `tool_permission_packet.v0` record per marked permission decision
- validates the projection against the vendored OEP schema before write
- carries the actor / release manifest / policy / model / credential surfaces that
  `StateSnapshot` does not bind natively

What it does not do:

- it does not call OPA, evaluate policy, or decide whether the tool call should run
- it does not replace LangGraph checkpoints, LangSmith traces, OTel spans, or your
  policy engine
- it does not provide atomic checkpoint-and-evidence commit semantics. The inner
  checkpointer is called first; the OEP validation and sink write happen afterward.
  With `on_error="raise"`, the caller sees the OEP failure, but the checkpoint may
  already be persisted. Do not treat the two as one transaction. See
  [`docs/operational_caveats.md`](operational_caveats.md) for the full caveat list.
- it does not coordinate writes from multiple Python processes. `LocalJsonlSink` uses
  an in-process lock. Multi-worker deployments need one JSONL file per process, an
  external collector, or a custom sink you own.
- it does not redact PII from `resource.uri` or any other free-text field. Treat the
  emitted JSONL as sensitive operational evidence; route it to your normal secure
  storage with the same care you treat a trace store or a secrets log.
- async sinks are deferred in v0.1.0. `aput()` still uses the synchronous sink
  interface; slow sinks can add latency to async graph runs.

Before forking this pattern into production, work through the checklist in
[`docs/operational_caveats.md`](operational_caveats.md) §Production Fork Checklist:
durable storage, redaction strategy, real policy response source, marker key
generation, concurrent emitter serialization, supported LangGraph versions,
schema-version roll-forward, retention and deletion.

The two replay primitives are not competing. Use LangGraph time travel for execution
recovery and branched exploration; use substitution-class replay when last week's
incident asks what would have changed had a stored surface been different. The wrapper
is the bridge between the LangGraph checkpoint event and a record that the
substitution-class layer can replay against.

---

## References

- [README](../README.md) — 60-second example
- [`docs/quickstart.md`](quickstart.md) — moving parts of the wrapper
- [`docs/usage.md`](usage.md) — marker semantics, decision-context scope, sinks
- [`docs/19_wrapper_injected_fields.md`](19_wrapper_injected_fields.md) — wrapper-injected field map
- [`docs/relation_to_oep.md`](relation_to_oep.md) — schema vendoring and version pinning
- [`docs/operational_caveats.md`](operational_caveats.md) — non-transactional emission, multi-process, async, production fork checklist
- [`docs/public_claims.md`](public_claims.md) — claim boundary phrases
- [`examples/01_code_review_agent`](../examples/01_code_review_agent) — the runnable scenario this walkthrough uses
- [`examples/04_multi_step_orchestration_with_policy`](../examples/04_multi_step_orchestration_with_policy) — multiple decisions under one policy bundle
- [`examples/05_interrupt_resume_with_model_version`](../examples/05_interrupt_resume_with_model_version) — approval capture and model-version drift
- [Operational Evidence Plane](https://github.com/agent-runtime-evidence/operational-evidence-plane) — counterfactual replay primitives (CR-002 / CR-003 / CR-004) operate on `tool_permission_packet.v0` records
- [LangGraph time-travel docs](https://docs.langchain.com/oss/python/langgraph/use-time-travel) — `Replay re-executes nodes — it doesn't just read from cache. LLM calls, API requests, and interrupts fire again and may return different results.`
- [LangGraph persistence docs](https://docs.langchain.com/oss/python/langgraph/persistence) — `Nodes after the checkpoint re-execute, including any LLM calls, API requests, or interrupts — which are always re-triggered during replay.`
- My arXiv preprint on the operational evidence plane — `arXiv:2605.12078`
