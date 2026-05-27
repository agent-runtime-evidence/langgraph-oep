# Changelog

All notable changes to `langgraph-oep` are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Nothing yet.

## [0.1.0] - 2026-05-27

### Added

- Initial public alpha release of the `langgraph-oep` checkpoint wrapper.
- `DecisionContext`, `OEPCheckpointSaver`, `attach_oep_writer`, JSONL/stdout
  sinks, OEP packet projection, and schema validation.
- Five runnable examples covering single-decision capture, scoped credentials,
  cache metadata, multi-step orchestration, and interrupt/resume metadata.
- CI coverage for LangGraph `0.2.x`, `0.3.x`, and `1.x`.

### Notes

- Public API introduced.
- Schema contract introduced through the vendored OEP
  `tool_permission_packet.v0` schema.
- This is an illustration-grade reference implementation, not a
  production-certified observability platform or official LangGraph
  integration.

[Unreleased]: https://github.com/agent-runtime-evidence/langgraph-oep/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/agent-runtime-evidence/langgraph-oep/releases/tag/v0.1.0
