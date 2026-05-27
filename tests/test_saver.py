from __future__ import annotations

import copy

import pytest

from langgraph_oep import OEP_EMIT_PERMISSION_CHANNEL, Actor, DecisionContext, OEPCheckpointSaver

from .helpers import FakeSaver, RecordingSink, permission_checkpoint, sample_policy_response


def test_saver_delegates_put_and_emits_packet_inside_context() -> None:
    inner = FakeSaver()
    sink = RecordingSink()
    saver = OEPCheckpointSaver(inner, sink, on_error="raise")
    checkpoint = permission_checkpoint()

    with DecisionContext(
        actor=Actor(type="agent", id="agent_test", display_name="Agent Test"),
        release_manifest_id="rmf_test",
        policy_bundle_version="sha256:" + "0" * 64,
        policy_response=sample_policy_response(),
    ):
        result = saver.put(
            {"configurable": {"thread_id": "t1"}},
            checkpoint,
            {"source": "loop", "step": 1},
            {},
        )

    assert result["configurable"]["checkpoint_id"] == checkpoint["id"]
    assert len(inner.put_calls) == 1
    assert len(sink.packets) == 1
    assert sink.packets[0]["tool"]["name"] == "read_diff"


def test_saver_skips_emit_without_context() -> None:
    inner = FakeSaver()
    sink = RecordingSink()
    saver = OEPCheckpointSaver(inner, sink, on_error="raise")

    saver.put({"configurable": {"thread_id": "t1"}}, permission_checkpoint(), {}, {})

    assert len(inner.put_calls) == 1
    assert sink.packets == []


def test_saver_deduplicates_carried_forward_marker_state() -> None:
    inner = FakeSaver()
    sink = RecordingSink()
    saver = OEPCheckpointSaver(inner, sink, on_error="raise")
    first = permission_checkpoint("ckpt_test_001")
    carried_forward = copy.deepcopy(first)
    carried_forward["id"] = "ckpt_test_002"
    carried_forward["ts"] = "2026-05-27T00:00:01Z"
    carried_forward["updated_channels"] = None

    with DecisionContext(
        actor=Actor(type="agent", id="agent_test", display_name="Agent Test"),
        release_manifest_id="rmf_test",
        policy_response=sample_policy_response(),
    ):
        saver.put({"configurable": {"thread_id": "t1"}}, first, {}, {})
        saver.put({"configurable": {"thread_id": "t1"}}, carried_forward, {}, {})

    assert len(sink.packets) == 1


def test_saver_allows_same_surface_with_distinct_explicit_markers() -> None:
    inner = FakeSaver()
    sink = RecordingSink()
    saver = OEPCheckpointSaver(inner, sink, on_error="raise")
    first = permission_checkpoint("ckpt_test_001")
    second = copy.deepcopy(first)
    first["channel_values"][OEP_EMIT_PERMISSION_CHANNEL] = "decision-a"
    second["id"] = "ckpt_test_002"
    second["channel_values"][OEP_EMIT_PERMISSION_CHANNEL] = "decision-b"

    with DecisionContext(
        actor=Actor(type="agent", id="agent_test", display_name="Agent Test"),
        release_manifest_id="rmf_test",
        policy_response=sample_policy_response(),
    ):
        saver.put({"configurable": {"thread_id": "t1"}}, first, {}, {})
        saver.put({"configurable": {"thread_id": "t1"}}, second, {}, {})

    assert len(sink.packets) == 2


def test_saver_allows_same_surface_with_distinct_metadata_markers() -> None:
    inner = FakeSaver()
    sink = RecordingSink()
    saver = OEPCheckpointSaver(inner, sink, on_error="raise")
    first = permission_checkpoint("ckpt_test_001")
    second = copy.deepcopy(first)
    second["id"] = "ckpt_test_002"

    with DecisionContext(
        actor=Actor(type="agent", id="agent_test", display_name="Agent Test"),
        release_manifest_id="rmf_test",
        policy_response=sample_policy_response(),
    ):
        saver.put(
            {"configurable": {"thread_id": "t1"}},
            first,
            {
                "writes": {
                    "unrelated_node": {OEP_EMIT_PERMISSION_CHANNEL: "unrelated-marker"},
                    "permission_node": {
                        OEP_EMIT_PERMISSION_CHANNEL: "decision-a",
                        "tool": first["channel_values"]["tool"],
                    }
                }
            },
            {},
        )
        saver.put(
            {"configurable": {"thread_id": "t1"}},
            second,
            {
                "writes": {
                    "unrelated_node": {OEP_EMIT_PERMISSION_CHANNEL: "unrelated-marker"},
                    "permission_node": {
                        OEP_EMIT_PERMISSION_CHANNEL: "decision-b",
                        "tool": second["channel_values"]["tool"],
                    }
                }
            },
            {},
        )

    assert len(sink.packets) == 2


def test_saver_on_error_raise() -> None:
    inner = FakeSaver()
    sink = RecordingSink()
    saver = OEPCheckpointSaver(inner, sink, on_error="raise")
    checkpoint = permission_checkpoint()
    del checkpoint["channel_values"]["resource"]

    with DecisionContext(
        actor=Actor(type="agent", id="agent_test", display_name="Agent Test"),
        release_manifest_id="rmf_test",
        policy_response=sample_policy_response(),
    ), pytest.raises(ValueError):
        saver.put({"configurable": {"thread_id": "t1"}}, checkpoint, {}, {})

    assert len(inner.put_calls) == 1
    assert sink.packets == []


def test_saver_on_error_drop() -> None:
    inner = FakeSaver()
    sink = RecordingSink()
    saver = OEPCheckpointSaver(inner, sink, on_error="drop")
    checkpoint = permission_checkpoint()
    del checkpoint["channel_values"]["resource"]

    with DecisionContext(
        actor=Actor(type="agent", id="agent_test", display_name="Agent Test"),
        release_manifest_id="rmf_test",
        policy_response=sample_policy_response(),
    ):
        saver.put({"configurable": {"thread_id": "t1"}}, checkpoint, {}, {})

    assert len(inner.put_calls) == 1
    assert sink.packets == []


async def test_async_put_emits_packet() -> None:
    inner = FakeSaver()
    sink = RecordingSink()
    saver = OEPCheckpointSaver(inner, sink, on_error="raise")

    with DecisionContext(
        actor=Actor(type="agent", id="agent_test", display_name="Agent Test"),
        release_manifest_id="rmf_test",
        policy_response=sample_policy_response(),
    ):
        await saver.aput({"configurable": {"thread_id": "t1"}}, permission_checkpoint(), {}, {})

    assert len(sink.packets) == 1


def test_other_methods_delegate() -> None:
    inner = FakeSaver()
    sink = RecordingSink()
    saver = OEPCheckpointSaver(inner, sink)

    saver.put_writes({"configurable": {"thread_id": "t1"}}, [("task", "value")], "task_id")
    saver.delete_thread("t1")

    assert inner.writes[0][2] == "task_id"
    assert inner.deleted_threads == ["t1"]
