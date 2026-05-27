from __future__ import annotations

import json

import pytest
from jsonschema import ValidationError

from langgraph_oep.validation import validate_packet

from .conftest import FIXTURES


def test_canonical_packet_validates_against_vendored_schema() -> None:
    packet = json.loads((FIXTURES / "code_review_tool_permission.v0.json").read_text())
    validate_packet(packet)


def test_validation_rejects_invalid_packet() -> None:
    packet = json.loads((FIXTURES / "code_review_tool_permission.v0.json").read_text())
    packet["packet_id"] = "bad"

    with pytest.raises(ValidationError):
        validate_packet(packet)


def test_validation_rejects_invalid_datetime_format() -> None:
    packet = json.loads((FIXTURES / "code_review_tool_permission.v0.json").read_text())
    packet["decision_time"] = "not-a-date-time"

    with pytest.raises(ValidationError):
        validate_packet(packet)
