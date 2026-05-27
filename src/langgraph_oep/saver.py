"""LangGraph checkpointer wrapper that emits OEP records on checkpoint writes."""

from __future__ import annotations

import json
import logging
from collections.abc import (
    AsyncIterator,
    Awaitable,
    Callable,
    Collection,
    Iterator,
    Mapping,
    Sequence,
)
from threading import Lock
from typing import Any, Literal, cast

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)

from langgraph_oep.context import DecisionContext
from langgraph_oep.mapping import OEP_EMIT_PERMISSION_CHANNEL
from langgraph_oep.projection import PERMISSION_CHANNELS, project_checkpoint_to_oep
from langgraph_oep.sinks.base import OEPSink
from langgraph_oep.validation import validate_packet

logger = logging.getLogger(__name__)

OnError = Literal["raise", "log", "drop"]


class OEPCheckpointSaver(BaseCheckpointSaver[Any]):
    """Composition wrapper around a LangGraph checkpointer."""

    def __init__(
        self,
        inner: BaseCheckpointSaver[Any],
        sink: OEPSink,
        *,
        on_error: OnError = "log",
    ) -> None:
        if on_error not in {"raise", "log", "drop"}:
            raise ValueError("on_error must be one of: raise, log, drop")
        super().__init__(serde=inner.serde)
        self._inner = inner
        self._sink = sink
        self._on_error = on_error
        self._emitted_keys: set[str] = set()
        self._emitted_keys_lock = Lock()

    @property
    def inner(self) -> BaseCheckpointSaver[Any]:
        return self._inner

    @property
    def config_specs(self) -> list[Any]:
        return self._inner.config_specs

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        result = self._inner.put(config, checkpoint, metadata, new_versions)
        self._emit(config, checkpoint, metadata)
        return result

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        result = await self._inner.aput(config, checkpoint, metadata, new_versions)
        self._emit(config, checkpoint, metadata)
        return result

    def _emit(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
    ) -> None:
        try:
            packet = project_checkpoint_to_oep(config, checkpoint, metadata, DecisionContext.current())
            if packet is None:
                return
            validate_packet(packet)
            dedupe_key = self._dedupe_key(packet, checkpoint, metadata)
            if not self._reserve_dedupe_key(dedupe_key):
                return
            try:
                self._sink.write(packet)
            except Exception:
                self._release_dedupe_key(dedupe_key)
                raise
        except Exception as exc:
            self._handle_error(exc)

    def _handle_error(self, exc: Exception) -> None:
        if self._on_error == "raise":
            raise exc
        if self._on_error == "log":
            logger.warning("langgraph-oep projection failed: %s", exc)

    def _optional_inner_method(self, name: str) -> Any:
        method = getattr(self._inner, name, None)
        if method is None:
            raise NotImplementedError(
                f"Inner checkpoint saver {type(self._inner).__name__} does not implement {name}."
            )
        return method

    def _reserve_dedupe_key(self, key: str) -> bool:
        with self._emitted_keys_lock:
            if key in self._emitted_keys:
                return False
            self._emitted_keys.add(key)
            return True

    def _release_dedupe_key(self, key: str) -> None:
        with self._emitted_keys_lock:
            self._emitted_keys.discard(key)

    def _explicit_marker_key(self, marker: Any) -> str | None:
        if isinstance(marker, str) and marker:
            return f"marker:{marker}"
        if isinstance(marker, dict):
            marker_id = marker.get("decision_key") or marker.get("id")
            if marker_id:
                return f"marker:{marker_id}"
        return None

    def _metadata_marker_key(self, metadata: CheckpointMetadata) -> str | None:
        writes = metadata.get("writes")
        if not isinstance(writes, Mapping):
            return None
        for write in writes.values():
            if not isinstance(write, Mapping):
                continue
            if not self._metadata_write_touches_permission(write):
                continue
            marker_key = self._explicit_marker_key(write.get(OEP_EMIT_PERMISSION_CHANNEL))
            if marker_key is not None:
                return marker_key
        return None

    def _metadata_write_touches_permission(self, write: Mapping[str, Any]) -> bool:
        for channel in PERMISSION_CHANNELS:
            value = write.get(channel)
            if value is None:
                continue
            if isinstance(value, Mapping) and len(value) == 0:
                continue
            return True
        return False

    def _dedupe_key(
        self,
        packet: dict[str, Any],
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
    ) -> str:
        marker_key = self._metadata_marker_key(metadata)
        if marker_key is not None:
            return marker_key

        marker = checkpoint.get("channel_values", {}).get(OEP_EMIT_PERMISSION_CHANNEL)
        marker_key = self._explicit_marker_key(marker)
        if marker_key is not None:
            return marker_key

        stable_surface = {
            "actor": packet.get("actor"),
            "trace_id": packet.get("trace_id"),
            "release_manifest_id": packet.get("release_manifest_id"),
            "requested_action": packet.get("requested_action"),
            "tool": packet.get("tool"),
            "resource": packet.get("resource"),
            "policy": packet.get("policy"),
            "decision": packet.get("decision"),
        }
        return "surface:" + json.dumps(stable_surface, sort_keys=True, separators=(",", ":"))

    def get(self, config: RunnableConfig) -> Checkpoint | None:
        return self._inner.get(config)

    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        return self._inner.get_tuple(config)

    def list(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> Iterator[CheckpointTuple]:
        return self._inner.list(config, filter=filter, before=before, limit=limit)

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        self._inner.put_writes(config, writes, task_id, task_path)

    def delete_thread(self, thread_id: str) -> None:
        self._inner.delete_thread(thread_id)

    def delete_for_runs(self, run_ids: Sequence[str]) -> None:
        method = cast(Callable[[Sequence[str]], None], self._optional_inner_method("delete_for_runs"))
        method(run_ids)

    def copy_thread(self, source_thread_id: str, target_thread_id: str) -> None:
        method = cast(Callable[[str, str], None], self._optional_inner_method("copy_thread"))
        method(source_thread_id, target_thread_id)

    def prune(self, thread_ids: Sequence[str], *, strategy: str = "keep_latest") -> None:
        method = cast(
            Callable[..., None],
            self._optional_inner_method("prune"),
        )
        method(thread_ids, strategy=strategy)

    def get_delta_channel_history(
        self,
        *,
        config: RunnableConfig,
        channels: Sequence[str],
    ) -> Mapping[str, Any]:
        method = cast(
            Callable[..., Mapping[str, Any]],
            self._optional_inner_method("get_delta_channel_history"),
        )
        return method(config=config, channels=channels)

    def get_next_version(self, current: Any, channel: Any) -> Any:
        return self._inner.get_next_version(current, channel)

    def with_allowlist(
        self,
        extra_allowlist: Collection[tuple[str, ...]],
    ) -> OEPCheckpointSaver:
        method = cast(
            Callable[[Collection[tuple[str, ...]]], BaseCheckpointSaver[Any]],
            self._optional_inner_method("with_allowlist"),
        )
        return OEPCheckpointSaver(
            method(extra_allowlist),
            self._sink,
            on_error=self._on_error,
        )

    async def aget(self, config: RunnableConfig) -> Checkpoint | None:
        return await self._inner.aget(config)

    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        return await self._inner.aget_tuple(config)

    async def alist(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[CheckpointTuple]:
        async for item in self._inner.alist(config, filter=filter, before=before, limit=limit):
            yield item

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        await self._inner.aput_writes(config, writes, task_id, task_path)

    async def adelete_thread(self, thread_id: str) -> None:
        await self._inner.adelete_thread(thread_id)

    async def adelete_for_runs(self, run_ids: Sequence[str]) -> None:
        method = cast(
            Callable[[Sequence[str]], Awaitable[None]],
            self._optional_inner_method("adelete_for_runs"),
        )
        await method(run_ids)

    async def acopy_thread(self, source_thread_id: str, target_thread_id: str) -> None:
        method = cast(Callable[[str, str], Awaitable[None]], self._optional_inner_method("acopy_thread"))
        await method(source_thread_id, target_thread_id)

    async def aprune(self, thread_ids: Sequence[str], *, strategy: str = "keep_latest") -> None:
        method = cast(
            Callable[..., Awaitable[None]],
            self._optional_inner_method("aprune"),
        )
        await method(thread_ids, strategy=strategy)

    async def aget_delta_channel_history(
        self,
        *,
        config: RunnableConfig,
        channels: Sequence[str],
    ) -> Mapping[str, Any]:
        method = cast(
            Callable[..., Awaitable[Mapping[str, Any]]],
            self._optional_inner_method("aget_delta_channel_history"),
        )
        return await method(config=config, channels=channels)
