# 19 Wrapper-Injected Fields

The projection maps seven fields from LangGraph-native state channel values: tool name, tool version, tool operation, requested action input ref, requested action type, requested action name, and resource.

The wrapper-injected evidence fields are:

| Wrapper field | OEP field |
|---|---|
| `wrapper.session.tool_call_id` | `tool_call_id` |
| `wrapper.session.event_id` | `event_id` |
| `wrapper.session.trace_id` | `trace_id` |
| `wrapper.session.span_id` | `span_id` |
| `wrapper.session.release_manifest_id` | `release_manifest_id` |
| `wrapper.session.packet_id` | `packet_id` |
| `wrapper.session.decision_time` | `decision_time` |
| `wrapper.actor` | `actor` |
| `wrapper.policy_response.policy_ref` | `policy` |
| `wrapper.policy_response.decision` | `decision` |
| `wrapper.policy_response.links` | `links` |
| `wrapper.session.scoped_credential_lifetime` | `scoped_credential_lifetime` |
| `wrapper.session.approval_capture` | `approval_capture` |
| `wrapper.session.policy_bundle_version` | `policy_bundle_version` |
| `wrapper.session.release_manifest_version` | `release_manifest_version` |
| `wrapper.session.model_binding.alias` | `model_alias` |
| `wrapper.session.model_binding.resolved_version` | `resolved_model_version` |
| `wrapper.session.model_binding.provider` | `model_provider` |
| `wrapper.session.decision_id` | `decision_id` |

`claim_boundary` is also emitted as required schema context, but it is not counted as one of the 19 evidence surfaces.
