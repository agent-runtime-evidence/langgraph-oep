# ruff: noqa: E402, I001
from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from examples._shared import run_single_decision
from langgraph_oep import Actor, ModelBinding

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "oep-records.jsonl"

result = run_single_decision(
    output_path=OUTPUT,
    thread_id="rag-demo-001",
    actor=Actor(type="agent", id="agent_rag_demo", display_name="rag-agent-demo"),
    release_manifest_id="rmf_rag_2026_06",
    tool={"name": "retrieve_context", "version": "0.1.0", "operation": "read"},
    requested_action={
        "action_type": "retrieve_context",
        "name": "retrieve cached policy context",
        "input_ref": "rag/query_0001",
    },
    resource={
        "type": "retrieval_cache",
        "id": "cache_hit_policy_0001",
        "uri": "cache/policy/context/0001",
        "mutable": False,
    },
    result_text="retrieved cached context with similarity 0.92",
    packet_id="pder_rag_cache_0001",
    event_id="evt_rag_cache_0001",
    tool_call_id="tool_rag_cache_0001",
    trace_id="55555555555555555555555555555555",
    span_id="6666666666666666",
    decision_time="2026-06-01T00:10:00Z",
    policy_bundle_version="sha256:" + "3" * 64,
    model_binding=ModelBinding(alias="rag-ranker", resolved_version="0.1.0", provider="internal"),
    decision_id_extras={
        "cache": {
            "cache_hit_id": "cache_policy_context_0001",
            "cache_version": "rag-cache.v1",
            "embedding_model_version": "text-embedding-demo-0.1.0",
            "staleness_flag": False,
            "cache_correctness_status": "accepted",
            "similarity_score": 0.92,
            "invalidation_event_id": None,
        }
    },
)

print(result["output"])
print(f"OEP records written to {OUTPUT}")
