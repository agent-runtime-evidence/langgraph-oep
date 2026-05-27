"""Project LangGraph checkpoint writes into OEP tool_permission_packet.v0 records."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import Checkpoint, CheckpointMetadata

from langgraph_oep.context import DecisionContext
from langgraph_oep.decision_id import build_decision_id
from langgraph_oep.ids import generate_per_checkpoint_ids
from langgraph_oep.mapping import OEP_EMIT_PERMISSION_CHANNEL

OEP_SCHEMA_VERSION = "oep.tool_permission_packet.v0"
PERMISSION_CHANNELS = frozenset({"tool", "requested_action", "resource"})
_MISSING = object()


def _required(value: Any, field: str) -> Any:
    if value is None:
        raise ValueError(f"LangGraph checkpoint missing required OEP field: {field}")
    return value


def _required_mapping(value: Any, field: str) -> Mapping[str, Any]:
    value = _required(value, field)
    if not isinstance(value, Mapping):
        raise TypeError(f"LangGraph checkpoint field must be a mapping: {field}")
    return cast(Mapping[str, Any], value)


def _placeholder_policy_response(
    *,
    event_id: str,
    release_manifest_id: str,
    trace_id: str,
) -> dict[str, Any]:
    return {
        "policy_ref": {
            "engine": "opa",
            "package": "data.langgraph_oep.default",
            "policy_id": "langgraph-oep-default-policy",
            "policy_version": "0.1.0",
            "policy_uri": "langgraph-oep://default-policy",
        },
        "decision": {
            "allow": True,
            "reason": "langgraph-oep default decision placeholder; pass policy_response for environment-specific policy evidence",
            "matched_rule": "langgraph_oep_default_allow",
            "opa_result_ref": "langgraph-oep://default-decision",
        },
        "links": {
            "event_ref": f"langgraph-oep://events/{event_id}",
            "release_manifest_ref": f"langgraph-oep://release-manifests/{release_manifest_id}",
            "trace_ref": f"langgraph-oep://traces/{trace_id}",
        },
    }


def _is_empty_surface(value: Any) -> bool:
    return value is None or (isinstance(value, Mapping) and len(value) == 0)


def _has_no_permission_surface(values: Mapping[str, Any]) -> bool:
    return (
        _is_empty_surface(values.get("tool"))
        and _is_empty_surface(values.get("requested_action"))
        and _is_empty_surface(values.get("resource"))
    )


def _write_touches_permission(write: Mapping[str, Any]) -> bool:
    return any(not _is_empty_surface(write.get(channel)) for channel in PERMISSION_CHANNELS)


def _metadata_writes_touch_permission(metadata: Mapping[str, Any]) -> bool | None:
    writes = metadata.get("writes")
    if writes is None:
        return None
    if not isinstance(writes, Mapping):
        return None
    for write in writes.values():
        if not isinstance(write, Mapping):
            continue
        if _write_touches_permission(write):
            return True
    return False


def _is_emit_marker(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, str):
        return len(value) > 0
    if isinstance(value, Mapping):
        if value.get("emit") is False:
            return False
        return bool(value.get("decision_key") or value.get("id") or value.get("emit") is True)
    return False


def _metadata_writes_emit_marker(metadata: Mapping[str, Any]) -> bool | None:
    writes = metadata.get("writes")
    if writes is None:
        return None
    if not isinstance(writes, Mapping):
        return None
    for write in writes.values():
        if not isinstance(write, Mapping):
            continue
        marker = write.get(OEP_EMIT_PERMISSION_CHANNEL, _MISSING)
        if (
            marker is not _MISSING
            and _is_emit_marker(marker)
            and _write_touches_permission(write)
        ):
            return True
    return False


def _checkpoint_has_emit_marker(
    *,
    values: Mapping[str, Any],
    checkpoint: Checkpoint,
    metadata: CheckpointMetadata,
) -> bool:
    metadata_marker = _metadata_writes_emit_marker(metadata)
    if metadata_marker is not None:
        return metadata_marker

    updated_channels = checkpoint.get("updated_channels")
    if updated_channels is not None:
        return OEP_EMIT_PERMISSION_CHANNEL in updated_channels and (
            _is_emit_marker(values.get(OEP_EMIT_PERMISSION_CHANNEL))
        )

    return _is_emit_marker(values.get(OEP_EMIT_PERMISSION_CHANNEL))


def _policy_response_for_context(
    *,
    ctx: DecisionContext,
    event_id: str,
    release_manifest_id: str,
    trace_id: str,
) -> dict[str, Any]:
    if ctx.policy_response is not None:
        return dict(ctx.policy_response)
    if ctx.allow_placeholder_policy_response:
        return _placeholder_policy_response(
            event_id=event_id,
            release_manifest_id=release_manifest_id,
            trace_id=trace_id,
        )
    raise ValueError(
        "DecisionContext.policy_response is required for OEP emission. "
        "Pass the captured policy decision, or set "
        "allow_placeholder_policy_response=True only for examples/tests."
    )


def project_checkpoint_to_oep(
    config: RunnableConfig,
    checkpoint: Checkpoint,
    metadata: CheckpointMetadata,
    ctx: DecisionContext | None,
) -> dict[str, Any] | None:
    """Project one LangGraph checkpoint write into an OEP permission packet.

    Returns None when no DecisionContext is active or when the checkpoint has no
    tool/requested_action/resource permission surface.
    """

    del config
    if ctx is None:
        return None

    values = checkpoint.get("channel_values", {})
    if _has_no_permission_surface(values):
        return None
    if not _checkpoint_has_emit_marker(values=values, checkpoint=checkpoint, metadata=metadata):
        return None
    if _metadata_writes_touch_permission(metadata) is False:
        return None
    updated_channels = checkpoint.get("updated_channels")
    if updated_channels is not None and not PERMISSION_CHANNELS.intersection(updated_channels):
        return None

    tool = _required_mapping(values.get("tool"), "checkpoint.channel_values.tool")
    requested_action = _required_mapping(
        values.get("requested_action"),
        "checkpoint.channel_values.requested_action",
    )
    resource = _required_mapping(values.get("resource"), "checkpoint.channel_values.resource")

    generated_ids = generate_per_checkpoint_ids(checkpoint)
    packet_id = ctx.packet_id or generated_ids["packet_id"]
    event_id = ctx.event_id or generated_ids["event_id"]
    tool_call_id = ctx.tool_call_id or generated_ids["tool_call_id"]
    span_id = ctx.span_id or generated_ids["span_id"]
    trace_id = ctx.trace_id or generated_ids["span_id"] + generated_ids["span_id"]
    decision_time = ctx.decision_time or checkpoint["ts"]

    policy_response = _policy_response_for_context(
        ctx=ctx,
        event_id=event_id,
        release_manifest_id=ctx.release_manifest_id,
        trace_id=trace_id,
    )
    model_binding = ctx.model_binding.to_dict()

    packet: dict[str, Any] = {
        "schema_version": OEP_SCHEMA_VERSION,
        "packet_id": packet_id,
        "decision_time": decision_time,
        "release_manifest_id": ctx.release_manifest_id,
        "event_id": event_id,
        "tool_call_id": tool_call_id,
        "trace_id": trace_id,
        "span_id": span_id,
        "actor": ctx.actor_dict(),
        "requested_action": {
            "action_type": _required(
                requested_action.get("action_type"),
                "checkpoint.channel_values.requested_action.action_type",
            ),
            "name": _required(
                requested_action.get("name"),
                "checkpoint.channel_values.requested_action.name",
            ),
            "input_ref": _required(
                requested_action.get("input_ref"),
                "checkpoint.channel_values.requested_action.input_ref",
            ),
        },
        "tool": {
            "name": _required(tool.get("name"), "checkpoint.channel_values.tool.name"),
            "version": _required(tool.get("version"), "checkpoint.channel_values.tool.version"),
            "operation": _required(
                tool.get("operation"),
                "checkpoint.channel_values.tool.operation",
            ),
        },
        "resource": dict(resource),
        "policy": _required(policy_response.get("policy_ref"), "policy_response.policy_ref"),
        "decision": _required(policy_response.get("decision"), "policy_response.decision"),
        "scoped_credential_lifetime": ctx.scoped_credential_lifetime,
        "approval_capture": ctx.approval_capture,
        "policy_bundle_version": ctx.policy_bundle_version,
        "release_manifest_version": ctx.release_manifest_version,
        "model_alias": model_binding["alias"],
        "resolved_model_version": model_binding["resolved_version"],
        "model_provider": model_binding["provider"],
        "decision_id": build_decision_id(
            packet_id=packet_id,
            tool_call_id=tool_call_id,
            policy_bundle_version=ctx.policy_bundle_version,
            decision_id_extras=ctx.decision_id_extras,
        ),
        "links": _required(policy_response.get("links"), "policy_response.links"),
        "claim_boundary": ctx.claim_boundary,
    }
    if ctx.nd_builtin_cache is not None:
        packet["nd_builtin_cache"] = dict(ctx.nd_builtin_cache)
    return packet
