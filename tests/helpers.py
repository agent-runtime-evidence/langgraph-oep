from __future__ import annotations

from collections.abc import AsyncIterator, Iterator, Sequence
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)

from langgraph_oep import OEP_EMIT_PERMISSION_CHANNEL


class RecordingSink:
    def __init__(self) -> None:
        self.packets: list[dict[str, Any]] = []

    def write(self, packet: dict[str, Any]) -> None:
        self.packets.append(packet)


class FakeSaver(BaseCheckpointSaver[Any]):
    def __init__(self) -> None:
        super().__init__()
        self.put_calls: list[tuple[RunnableConfig, Checkpoint, CheckpointMetadata]] = []
        self.writes: list[tuple[RunnableConfig, Sequence[tuple[str, Any]], str, str]] = []
        self.deleted_threads: list[str] = []
        self.tuples: list[CheckpointTuple] = []

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        del new_versions
        self.put_calls.append((config, checkpoint, metadata))
        saved_config: RunnableConfig = {
            "configurable": {
                **config.get("configurable", {}),
                "checkpoint_id": checkpoint["id"],
            }
        }
        self.tuples.append(CheckpointTuple(saved_config, checkpoint, metadata))
        return saved_config

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        return self.put(config, checkpoint, metadata, new_versions)

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        self.writes.append((config, writes, task_id, task_path))

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        self.put_writes(config, writes, task_id, task_path)

    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        checkpoint_id = config.get("configurable", {}).get("checkpoint_id")
        for item in self.tuples:
            if item.config.get("configurable", {}).get("checkpoint_id") == checkpoint_id:
                return item
        return self.tuples[-1] if self.tuples else None

    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        return self.get_tuple(config)

    def list(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> Iterator[CheckpointTuple]:
        del config, filter, before
        yield from self.tuples[:limit]

    async def alist(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[CheckpointTuple]:
        for item in self.list(config, filter=filter, before=before, limit=limit):
            yield item

    def delete_thread(self, thread_id: str) -> None:
        self.deleted_threads.append(thread_id)


def permission_checkpoint(checkpoint_id: str = "ckpt_test_001") -> Checkpoint:
    return {
        "v": 1,
        "id": checkpoint_id,
        "ts": "2026-05-27T00:00:00Z",
        "channel_values": {
            "tool": {"name": "read_diff", "version": "0.1.0", "operation": "read"},
            "requested_action": {
                "action_type": "inspect_diff",
                "name": "inspect diff",
                "input_ref": "diff.patch",
            },
            "resource": {
                "type": "repository_diff",
                "id": "diff_001",
                "uri": "diff.patch",
                "mutable": False,
            },
            OEP_EMIT_PERMISSION_CHANNEL: True,
        },
        "channel_versions": {},
        "versions_seen": {},
        "updated_channels": ["tool", "requested_action", "resource", OEP_EMIT_PERMISSION_CHANNEL],
    }


def sample_policy_response() -> dict[str, Any]:
    return {
        "policy_ref": {
            "engine": "opa",
            "package": "data.langgraph_oep.tests",
            "policy_id": "test-policy",
            "policy_version": "0.1.0",
            "policy_uri": "tests/policy.rego",
        },
        "decision": {
            "allow": True,
            "reason": "test policy allows fixture action",
            "matched_rule": "allow_fixture_action",
            "opa_result_ref": "opa://tests/result",
        },
        "links": {
            "event_ref": "tests/events/event.json",
            "release_manifest_ref": "tests/manifest/release.json",
            "trace_ref": "tests/traces/trace.json",
        },
    }
