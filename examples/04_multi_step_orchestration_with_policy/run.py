# ruff: noqa: E402, I001
from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from examples._shared import run_single_decision
from langgraph_oep import Actor, ModelBinding

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "oep-records.jsonl"
POLICY_HASH = "sha256:" + "4" * 64
OUTPUT.unlink(missing_ok=True)

for index, tool_name in enumerate(("plan_steps", "execute_step", "verify_result"), start=1):
    run_single_decision(
        output_path=OUTPUT,
        thread_id=f"orchestration-demo-{index:03d}",
        actor=Actor(
            type="agent",
            id="agent_orchestration_demo",
            display_name="orchestration-agent-demo",
        ),
        release_manifest_id="rmf_orchestration_2026_06",
        tool={"name": tool_name, "version": "0.1.0", "operation": "execute"},
        requested_action={
            "action_type": tool_name,
            "name": f"{tool_name.replace('_', ' ')} for orchestration demo",
            "input_ref": f"orchestration/step_{index}",
        },
        resource={
            "type": "orchestration_step",
            "id": f"step_{index}",
            "uri": f"orchestration/step_{index}",
            "mutable": True,
        },
        result_text=f"{tool_name} completed",
        packet_id=f"pder_orchestration_{index:04d}",
        event_id=f"evt_orchestration_{index:04d}",
        tool_call_id=f"tool_orchestration_{index:04d}",
        trace_id="77777777777777777777777777777777",
        span_id=f"{index:016x}",
        decision_time=f"2026-06-01T00:1{index}:00Z",
        policy_bundle_version=POLICY_HASH,
        model_binding=ModelBinding(alias="orchestrator", resolved_version="0.1.0", provider="internal"),
        reset_output=index == 1,
    )

print(f"OEP records written to {OUTPUT}")
