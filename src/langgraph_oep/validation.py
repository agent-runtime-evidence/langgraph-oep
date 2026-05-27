"""JSON Schema validation for emitted OEP permission packets."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime
from functools import lru_cache
from importlib.resources import files
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

SCHEMA_RESOURCE = "tool_permission_packet.v0.schema.json"


def _format_checker() -> FormatChecker:
    checker = FormatChecker()

    @checker.checks("date-time")  # type: ignore[untyped-decorator]
    def is_datetime(value: object) -> bool:
        if not isinstance(value, str):
            return True
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return False
        return parsed.tzinfo is not None

    return checker


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    schema_text = (
        files("langgraph_oep")
        .joinpath("schemas")
        .joinpath(SCHEMA_RESOURCE)
        .read_text(encoding="utf-8")
    )
    schema = json.loads(schema_text)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(
        schema,
        format_checker=_format_checker(),
    )


def validate_packet(packet: Mapping[str, Any]) -> None:
    """Raise jsonschema.ValidationError if a packet violates the vendored schema."""

    _validator().validate(dict(packet))
