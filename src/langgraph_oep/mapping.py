"""LangGraph checkpoint-to-OEP mapping constants."""

from __future__ import annotations

OEP_EMIT_PERMISSION_CHANNEL = "oep_emit_permission"

LANGGRAPH_NATIVE_FIELDS: list[tuple[str, str]] = [
    ("langgraph.state_snapshot.values.tool.name", "tool.name"),
    ("langgraph.state_snapshot.values.tool.version", "tool.version"),
    ("langgraph.state_snapshot.values.tool.operation", "tool.operation"),
    ("langgraph.state_snapshot.values.requested_action.input_ref", "requested_action.input_ref"),
    ("langgraph.state_snapshot.values.requested_action.action_type", "requested_action.action_type"),
    ("langgraph.state_snapshot.values.requested_action.name", "requested_action.name"),
    ("langgraph.state_snapshot.values.resource", "resource"),
]

WRAPPER_INJECTED_FIELDS: list[tuple[str, str]] = [
    ("wrapper.session.tool_call_id", "tool_call_id"),
    ("wrapper.session.event_id", "event_id"),
    ("wrapper.session.trace_id", "trace_id"),
    ("wrapper.session.span_id", "span_id"),
    ("wrapper.session.release_manifest_id", "release_manifest_id"),
    ("wrapper.session.packet_id", "packet_id"),
    ("wrapper.session.decision_time", "decision_time"),
    ("wrapper.actor", "actor"),
    ("wrapper.policy_response.policy_ref", "policy"),
    ("wrapper.policy_response.decision", "decision"),
    ("wrapper.policy_response.links", "links"),
    ("wrapper.session.scoped_credential_lifetime", "scoped_credential_lifetime"),
    ("wrapper.session.approval_capture", "approval_capture"),
    ("wrapper.session.policy_bundle_version", "policy_bundle_version"),
    ("wrapper.session.release_manifest_version", "release_manifest_version"),
    ("wrapper.session.model_binding.alias", "model_alias"),
    ("wrapper.session.model_binding.resolved_version", "resolved_model_version"),
    ("wrapper.session.model_binding.provider", "model_provider"),
    ("wrapper.session.decision_id", "decision_id"),
]

CLAIM_BOUNDARY_FIELD: tuple[str, str] = (
    "wrapper.session.claim_boundary",
    "claim_boundary",
)

assert len(LANGGRAPH_NATIVE_FIELDS) == 7
assert len(WRAPPER_INJECTED_FIELDS) == 19
