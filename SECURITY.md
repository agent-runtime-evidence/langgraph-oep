# Security Policy

## Supported Versions

`langgraph-oep` is a v0.1 alpha package. It is not production-certified and
does not provide security support for production deployments.

## Reporting a Vulnerability

Report security issues through GitHub Security Advisories once the public
repository is available, or email `dev404ai@gmail.com` as a fallback.

Please include:

- affected version and file or workflow;
- reproduction steps;
- expected and observed behavior;
- whether the issue affects local evidence emission, schema validation, or
  sensitive record handling.

OEP JSONL records can contain actor IDs, resource URIs, trace references,
cache identifiers, policy refs, scoped credential metadata, and approval
metadata. Treat generated records as sensitive operational evidence.
