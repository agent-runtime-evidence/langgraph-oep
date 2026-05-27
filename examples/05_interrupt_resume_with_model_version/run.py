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
    thread_id="interrupt-demo-001",
    actor=Actor(type="agent", id="agent_interrupt_demo", display_name="interrupt-agent-demo"),
    release_manifest_id="rmf_interrupt_2026_06",
    tool={"name": "resume_after_approval", "version": "0.1.0", "operation": "execute"},
    requested_action={
        "action_type": "resume_with_approval",
        "name": "resume after human approval",
        "input_ref": "interrupt/request_0001",
    },
    resource={
        "type": "approval_gate",
        "id": "approval_gate_0001",
        "uri": "interrupt/approval_gate_0001",
        "mutable": True,
    },
    result_text="resumed after approval with captured model version",
    packet_id="pder_interrupt_resume_0001",
    event_id="evt_interrupt_resume_0001",
    tool_call_id="tool_interrupt_resume_0001",
    trace_id="88888888888888888888888888888888",
    span_id="9999999999999999",
    decision_time="2026-06-01T00:20:00Z",
    policy_bundle_version="sha256:" + "5" * 64,
    model_binding=ModelBinding(
        alias="approval-reasoner",
        resolved_version="approval-reasoner-20260601",
        provider="internal",
    ),
    approval_capture={
        "approver": {"type": "human", "id": "human_reviewer_0001", "display_name": "Reviewer"},
        "captured_at": "2026-06-01T00:19:59Z",
        "approval_type": "manual_resume",
    },
    decision_id_extras={
        "drift": {
            "model_version": {
                "before_version": "approval-reasoner-20260531",
                "after_version": "approval-reasoner-20260601",
                "change_class": "alias_resolution",
                "attribution_confidence": 1,
            }
        }
    },
)

print(result["output"])
print(f"OEP records written to {OUTPUT}")
