from __future__ import annotations

from langgraph_oep.decision_id import build_decision_id


def test_decision_id_autopopulates_permission_join_surface() -> None:
    decision_id = build_decision_id(
        packet_id="pder_example",
        tool_call_id="tool_example",
        policy_bundle_version="sha256:" + "0" * 64,
        decision_id_extras={"cache": {"cache_hit_id": "cache_example"}},
    )

    assert decision_id["schema_version"] == "0.3"
    assert decision_id["permission"]["permission_packet_ref"] == "pder_example"
    assert decision_id["permission"]["tool_call_id"] == "tool_example"
    assert decision_id["permission"]["policy_bundle_version"] == "sha256:" + "0" * 64
    assert decision_id["cache"] == {"cache_hit_id": "cache_example"}
