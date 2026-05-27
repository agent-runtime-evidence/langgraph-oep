# Relation To OEP

This package vendors the OEP `tool_permission_packet.v0` schema so runtime validation does not depend on a local checkout of the main Operational Evidence Plane repository.

`langgraph-oep` versions independently from `operational-evidence-plane`. A package release pins the schema copy it vendors at release time; later OEP schema changes require an intentional package update.
