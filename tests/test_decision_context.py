from __future__ import annotations

import asyncio
import re

import pytest

from langgraph_oep import Actor, DecisionContext


async def _context_task(actor_id: str) -> str:
    with DecisionContext(
        actor=Actor(type="agent", id=actor_id, display_name=actor_id),
        release_manifest_id=f"rmf_{actor_id}",
    ) as ctx:
        await asyncio.sleep(0)
        current = DecisionContext.current()
        assert current is ctx
        assert ctx.trace_id is not None
        assert re.fullmatch(r"[a-f0-9]{32}", ctx.trace_id)
        return current.actor_dict()["id"]


async def test_contextvars_are_isolated_across_async_tasks() -> None:
    results = await asyncio.gather(_context_task("agent_a"), _context_task("agent_b"))
    assert sorted(results) == ["agent_a", "agent_b"]
    assert DecisionContext.current() is None


def test_decision_context_rejects_reentry() -> None:
    ctx = DecisionContext(
        actor=Actor(type="agent", id="agent_test", display_name="Agent Test"),
        release_manifest_id="rmf_test",
    )

    def reenter_context() -> None:
        with ctx:
            pass

    with ctx, pytest.raises(RuntimeError, match="single-use"):
        reenter_context()

    assert DecisionContext.current() is None


def test_decision_context_rejects_sequential_reuse() -> None:
    ctx = DecisionContext(
        actor=Actor(type="agent", id="agent_test", display_name="Agent Test"),
        release_manifest_id="rmf_test",
    )

    with ctx:
        pass

    def reuse_context() -> None:
        with ctx:
            pass

    with pytest.raises(RuntimeError, match="single-use"):
        reuse_context()

    assert DecisionContext.current() is None
