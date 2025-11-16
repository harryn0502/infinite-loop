"""Helper utilities for building agent state updates."""

from __future__ import annotations

from typing import Any, List

from .state import ObsState


def agent_state_update(
    state: ObsState,
    *,
    messages: List[Any] | None = None,
    active_agent: str | None = None,
    **updates: Any,
) -> ObsState:
    """
    Build a state update dict that preserves frequently reused fields.

    Args:
        state: Current state snapshot
        messages: New messages this agent emits (default empty list)
        active_agent: Name of the agent producing this update
        updates: Additional overrides (plan, last_rows, etc.)
    """
    response: ObsState = {
        "messages": messages or [],
        "active_agent": active_agent or state.get("active_agent", "router"),
        "last_rows": state.get("last_rows", []),
        "plan": state.get("plan", []),
        "plan_step_index": state.get("plan_step_index", 0),
        "plan_mode": state.get("plan_mode", "default"),
        "diagnostics_context": state.get("diagnostics_context", {"results": []}),
    }
    response.update(updates)
    return response
