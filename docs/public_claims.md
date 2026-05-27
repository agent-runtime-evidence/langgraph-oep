# Public Claims

Use these phrases:

- one inspectable wrapping pattern
- illustration-grade reference implementation
- different replay primitives at different layers
- captures surfaces LangGraph's StateSnapshot does not bind natively

Avoid endorsement, partnership, official-integration, replacement, or production-certified framing. LangGraph is the upstream runtime being wrapped, not the subject of a criticism.

Do not imply that generated records prove a policy decision unless `DecisionContext.policy_response` came from the user's policy engine. Placeholder policy responses are examples-only.

Do not describe `on_error="raise"` as an atomic checkpoint-and-evidence commit. It reports OEP emission failure after the inner checkpointer has already accepted the checkpoint.
