# Operational Caveats

## Non-Transactional Emission

The wrapper delegates to the inner LangGraph checkpointer first. OEP validation and sink write happen afterward.

With `on_error="raise"`, the caller sees the OEP failure, but the checkpoint may already be persisted. Do not treat this as an atomic checkpoint-and-evidence commit.

## Sensitive Output

OEP packets can include:

- actor identifiers
- resource URIs
- trace references
- cache identifiers
- policy references
- scoped credential metadata
- approval metadata

Handle JSONL output as sensitive operational evidence.

## Async Runs

`aput()` still uses the synchronous sink interface in v0.1.0. Slow sinks can add latency to async graph runs. For high-volume async workloads, use a fast local sink or a custom sink that queues work quickly.

## Multi-Process JSONL Writes

`LocalJsonlSink` uses an in-process lock. It does not coordinate writes from multiple Python processes.

For multi-worker deployments, use one JSONL file per process, a filesystem or object-store writer you control, or a collector service that accepts packets and owns durable append semantics.

## Production Fork Checklist

Before using this pattern in a production fork, decide:

- where packets are durably stored
- how PII/resource identifiers are redacted or protected
- where policy responses come from
- how marker decision keys are generated
- how concurrent emitters are serialized
- which LangGraph versions are supported
- how schema versions are rolled forward
- how emitted records are retained and deleted
