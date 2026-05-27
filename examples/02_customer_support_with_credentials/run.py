# ruff: noqa: E402, I001
from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from examples._shared import run_single_decision
from langgraph_oep import Actor, ModelBinding

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "oep-records.jsonl"
POLICY_HASH = "sha256:" + "2" * 64

result = run_single_decision(
    output_path=OUTPUT,
    thread_id="support-demo-001",
    actor=Actor(type="agent", id="agent_support_demo", display_name="support-agent-demo"),
    release_manifest_id="rmf_support_2026_06",
    tool={"name": "read_customer_profile", "version": "0.1.0", "operation": "read"},
    requested_action={
        "action_type": "read_profile",
        "name": "read customer profile for active support case",
        "input_ref": "support/case_0001",
    },
    resource={
        "type": "customer_profile",
        "id": "customer_0001",
        "uri": "support/customers/customer_0001",
        "mutable": False,
    },
    result_text="profile read under scoped credential",
    packet_id="pder_support_profile_0001",
    event_id="evt_support_profile_0001",
    tool_call_id="tool_support_profile_0001",
    trace_id="33333333333333333333333333333333",
    span_id="4444444444444444",
    decision_time="2026-06-01T00:05:00Z",
    policy_bundle_version=POLICY_HASH,
    model_binding=ModelBinding(alias="support-router", resolved_version="0.1.0", provider="internal"),
    scoped_credential_lifetime="PT5M",
    decision_id_extras={
        "cache": {
            "cache_hit_id": "cache_support_no_hit_0001",
            "cache_version": "support-cache.v0",
            "embedding_model_version": "not_applicable",
            "staleness_flag": False,
            "cache_correctness_status": "not_applicable",
            "similarity_score": 0,
            "invalidation_event_id": "evt_credential_revoked_0001",
        },
        "identity": {
            "agent_identity": {
                "type": "agent",
                "id": "agent_support_demo",
                "display_name": "support-agent-demo",
            },
            "policy_version": "0.1.0",
            "approval_capture_ref": None,
        },
    },
)

print(result["output"])
print(f"OEP records written to {OUTPUT}")
