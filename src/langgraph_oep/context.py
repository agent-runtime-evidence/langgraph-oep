"""Decision context carried across LangGraph checkpoint writes."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import Any

_current_context: ContextVar[DecisionContext | None] = ContextVar(
    "_langgraph_oep_decision_context",
    default=None,
)


@dataclass(frozen=True)
class Actor:
    """Actor identity projected into an OEP permission packet."""

    type: str
    id: str
    display_name: str

    def to_dict(self) -> dict[str, str]:
        return {"type": self.type, "id": self.id, "display_name": self.display_name}


@dataclass(frozen=True)
class ModelBinding:
    """Model binding active at decision time."""

    alias: str | None = None
    resolved_version: str | None = None
    provider: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "alias": self.alias,
            "resolved_version": self.resolved_version,
            "provider": self.provider,
        }


@dataclass
class DecisionContext:
    """Bind wrapper-injected evidence surfaces for a LangGraph execution."""

    actor: Actor | Mapping[str, str]
    release_manifest_id: str
    policy_bundle_version: str | None = None
    release_manifest_version: str | None = None
    model_binding: ModelBinding = field(default_factory=ModelBinding)
    scoped_credential_lifetime: str | None = None
    approval_capture: dict[str, Any] | None = None
    claim_boundary: str = (
        "Illustration-grade record; not a compliance, audit, or model-quality claim."
    )
    trace_id: str | None = None
    decision_id_extras: dict[str, Any] | None = None
    policy_response: Mapping[str, Any] | None = None
    allow_placeholder_policy_response: bool = False
    nd_builtin_cache: Mapping[str, Any] | None = None
    packet_id: str | None = None
    event_id: str | None = None
    tool_call_id: str | None = None
    span_id: str | None = None
    decision_time: str | None = None
    _used: bool = field(default=False, init=False, repr=False)
    _token: Token[DecisionContext | None] | None = field(default=None, init=False, repr=False)

    def __enter__(self) -> DecisionContext:
        if self._used:
            raise RuntimeError(
                "DecisionContext instances are single-use. "
                "Create a new DecisionContext for each execution scope."
            )
        if self._token is not None:
            raise RuntimeError(
                "DecisionContext instances are single-use while active. "
                "Create a new DecisionContext for nested or concurrent scopes."
            )
        self._used = True
        if self.trace_id is None:
            self.trace_id = uuid.uuid4().hex
        self._token = _current_context.set(self)
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        if self._token is not None:
            _current_context.reset(self._token)
            self._token = None

    @classmethod
    def current(cls) -> DecisionContext | None:
        """Return the currently active decision context, if any."""

        return _current_context.get()

    def actor_dict(self) -> dict[str, str]:
        if isinstance(self.actor, Actor):
            return self.actor.to_dict()
        return {
            "type": str(self.actor["type"]),
            "id": str(self.actor["id"]),
            "display_name": str(self.actor["display_name"]),
        }


def decision_context(
    *,
    actor_id: str,
    actor_display_name: str,
    release_manifest_id: str,
    actor_type: str = "agent",
    **kwargs: Any,
) -> DecisionContext:
    """Build a DecisionContext from primitive keyword arguments."""

    return DecisionContext(
        actor=Actor(type=actor_type, id=actor_id, display_name=actor_display_name),
        release_manifest_id=release_manifest_id,
        **kwargs,
    )
