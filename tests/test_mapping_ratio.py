from __future__ import annotations

from langgraph_oep.mapping import LANGGRAPH_NATIVE_FIELDS, WRAPPER_INJECTED_FIELDS


def test_mapping_ratio_is_7_native_to_19_wrapper_injected() -> None:
    assert len(LANGGRAPH_NATIVE_FIELDS) == 7
    assert len(WRAPPER_INJECTED_FIELDS) == 19
