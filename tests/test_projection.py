from __future__ import annotations

import json
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import Checkpoint

from langgraph_oep import OEP_EMIT_PERMISSION_CHANNEL, Actor, DecisionContext, ModelBinding
from langgraph_oep.projection import project_checkpoint_to_oep

from .conftest import FIXTURES
from .helpers import permission_checkpoint, sample_policy_response


def _load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _checkpoint_from_fixture(fixture: dict[str, Any]) -> Checkpoint:
    langgraph = fixture["langgraph"]
    snapshot = langgraph["state_snapshot"]
    values = {**snapshot["values"], OEP_EMIT_PERMISSION_CHANNEL: True}
    return {
        "v": 1,
        "id": langgraph["checkpoint_id"],
        "ts": snapshot["created_at"],
        "channel_values": values,
        "channel_versions": {},
        "versions_seen": {},
        "updated_channels": list(values),
    }


def _context_from_fixture(fixture: dict[str, Any]) -> DecisionContext:
    wrapper = fixture["wrapper"]
    session = wrapper["session"]
    model_binding = session["model_binding"]
    return DecisionContext(
        actor=Actor(**wrapper["actor"]),
        release_manifest_id=session["release_manifest_id"],
        policy_bundle_version=session["policy_bundle_version"],
        release_manifest_version=session["release_manifest_version"],
        model_binding=ModelBinding(
            alias=model_binding["alias"],
            resolved_version=model_binding["resolved_version"],
            provider=model_binding["provider"],
        ),
        scoped_credential_lifetime=session["scoped_credential_lifetime"],
        approval_capture=session["approval_capture"],
        claim_boundary=session["claim_boundary"],
        trace_id=session["trace_id"],
        decision_id_extras=session["decision_id"],
        policy_response=wrapper["policy_response"],
        packet_id=session["packet_id"],
        event_id=session["event_id"],
        tool_call_id=session["tool_call_id"],
        span_id=session["span_id"],
        decision_time=session["decision_time"],
    )


def test_fixture_projection_matches_canonical_oep_packet() -> None:
    fixture = _load_fixture("code_review_checkpoint.v0.json")
    canonical = _load_fixture("code_review_tool_permission.v0.json")
    config: RunnableConfig = {
        "configurable": {"thread_id": "code-review-reference-demo"},
    }

    projected = project_checkpoint_to_oep(
        config,
        _checkpoint_from_fixture(fixture),
        {
            **fixture["langgraph"]["state_snapshot"]["metadata"],
            "writes": {
                "request_diff_inspection": {
                    OEP_EMIT_PERMISSION_CHANNEL: True,
                    "tool": {"name": "read_diff"},
                }
            },
        },
        _context_from_fixture(fixture),
    )

    assert projected == canonical


def test_projection_skips_non_permission_checkpoint() -> None:
    checkpoint: Checkpoint = {
        "v": 1,
        "id": "ckpt_no_permission",
        "ts": "2026-05-27T00:00:00Z",
        "channel_values": {"messages": []},
        "channel_versions": {},
        "versions_seen": {},
        "updated_channels": ["messages"],
    }
    ctx = DecisionContext(
        actor=Actor(type="agent", id="agent_test", display_name="Agent Test"),
        release_manifest_id="rmf_test",
    )

    assert project_checkpoint_to_oep({}, checkpoint, {}, ctx) is None


def test_projection_requires_explicit_emit_marker() -> None:
    checkpoint = permission_checkpoint()
    del checkpoint["channel_values"][OEP_EMIT_PERMISSION_CHANNEL]
    checkpoint["updated_channels"] = ["tool", "requested_action", "resource"]
    ctx = DecisionContext(
        actor=Actor(type="agent", id="agent_test", display_name="Agent Test"),
        release_manifest_id="rmf_test",
        policy_response={
            "policy_ref": {
                "engine": "opa",
                "package": "data.tests",
                "policy_id": "policy",
                "policy_version": "0.1.0",
                "policy_uri": "policy.rego",
            },
            "decision": {
                "allow": True,
                "reason": "allowed",
                "matched_rule": "allow",
                "opa_result_ref": "opa://result",
            },
            "links": {
                "event_ref": "events/event.json",
                "release_manifest_ref": "manifest/release.json",
                "trace_ref": None,
            },
        },
    )

    assert project_checkpoint_to_oep({}, checkpoint, {}, ctx) is None


def test_projection_uses_any_valid_metadata_emit_marker() -> None:
    checkpoint = permission_checkpoint()
    ctx = DecisionContext(
        actor=Actor(type="agent", id="agent_test", display_name="Agent Test"),
        release_manifest_id="rmf_test",
        policy_response=sample_policy_response(),
    )

    projected = project_checkpoint_to_oep(
        {},
        checkpoint,
        {
            "writes": {
                "first_node": {OEP_EMIT_PERMISSION_CHANNEL: False},
                "permission_node": {
                    OEP_EMIT_PERMISSION_CHANNEL: "decision_001",
                    "tool": {"name": "read_diff"},
                },
            }
        },
        ctx,
    )

    assert projected is not None
    assert projected["tool"]["name"] == "read_diff"


def test_projection_requires_metadata_marker_on_permission_write() -> None:
    checkpoint = permission_checkpoint()
    ctx = DecisionContext(
        actor=Actor(type="agent", id="agent_test", display_name="Agent Test"),
        release_manifest_id="rmf_test",
        policy_response=sample_policy_response(),
    )

    projected = project_checkpoint_to_oep(
        {},
        checkpoint,
        {
            "writes": {
                "unrelated_node": {OEP_EMIT_PERMISSION_CHANNEL: "decision_001"},
                "permission_node": {"tool": {"name": "read_diff"}},
            }
        },
        ctx,
    )

    assert projected is None


def test_projection_requires_policy_response_by_default() -> None:
    checkpoint = permission_checkpoint()
    ctx = DecisionContext(
        actor=Actor(type="agent", id="agent_test", display_name="Agent Test"),
        release_manifest_id="rmf_test",
    )

    try:
        project_checkpoint_to_oep({}, checkpoint, {}, ctx)
    except ValueError as exc:
        assert "policy_response is required" in str(exc)
    else:
        raise AssertionError("expected missing policy_response to raise")
