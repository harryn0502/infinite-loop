"""Routing agent for the observability multi-agent system."""

from typing import Any, Optional

from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from ..core.state import ObsState, AgentName
from ..core.state_utils import agent_state_update
from ..utils.diagnostics import (
    DEFAULT_DIAGNOSTIC_WINDOW_HOURS,
    extract_window_hours_from_text,
    infer_target_metric,
    is_diagnostics_intent,
)

DISALLOWED_KEYWORDS = [
    "delete",
    "drop",
    "destroy",
    "truncate",
    "wipe",
    "shutdown",
    "disable",
    "attack",
]

ANALYTICS_KEYWORDS = [
    "latency",
    "delay",
    "token",
    "metric",
    "data",
    "run",
    "agent",
    "tool",
    "chart",
    "graph",
    "observability",
]

REFUSAL_MESSAGE = (
    "I cannot help with this request as it is either unrelated to observability analysis "
    "or could potentially harm the system. If you need token/metrics/chart analysis, "
    "please be specific about your requirements."
)


class RoutingDecision(BaseModel):
    """LLM-based routing decision with reasoning."""

    agent: AgentName = Field(
        description="Agent to handle this request: planner, metrics_agent, or chart_agent"
    )
    reasoning: str = Field(
        description="Brief explanation of why this agent was chosen"
    )


def _extract_last_user_message(state: ObsState) -> Optional[HumanMessage]:
    return next(
        (
            m
            for m in reversed(state.get("messages", []))
            if hasattr(m, "type") and m.type == "human" and isinstance(m, HumanMessage)
        ),
        None,
    )


def _enter_diagnostics_mode(
    state: ObsState,
    text: str,
) -> bool:
    if not is_diagnostics_intent(text):
        return False

    detected_hours = extract_window_hours_from_text(text)
    window_hours = detected_hours or DEFAULT_DIAGNOSTIC_WINDOW_HOURS
    target_metric = infer_target_metric(text)

    state["plan_mode"] = "diagnostics"
    state["diagnostics_context"] = {
        "target_metric": target_metric,
        "baseline_window_hours": window_hours,
        "recent_window_hours": window_hours,
        "results": [],
    }
    print("🧭 Routing: planner (diagnostics mode)")
    return True


def _is_disallowed_request(text: str) -> bool:
    lowered = (text or "").lower()
    return any(keyword in lowered for keyword in DISALLOWED_KEYWORDS)


def _is_analytics_request(text: str) -> bool:
    lowered = (text or "").lower()
    return any(keyword in lowered for keyword in ANALYTICS_KEYWORDS)


def _route_default_flow(state: ObsState, llm, user_text: str) -> AgentName:
    text = (user_text or "").lower()
    has_data = bool(state.get("last_rows"))

    chart_keywords = [
        "chart",
        "graph",
        "plot",
        "visualize",
        "bar chart",
        "line chart",
        "pie chart",
        "visualization",
    ]
    matched_chart_keyword = next((kw for kw in chart_keywords if kw in text), None)
    if matched_chart_keyword:
        if has_data:
            print(f"🧭 Routing: chart_agent (keyword match '{matched_chart_keyword}')")
            return "chart_agent"
        print(
            "🧭 Routing: planner (chart keyword detected but no cached data; "
            "need plan to fetch data before chart)"
        )
        return "planner"

    context_hint = SystemMessage(
        content=(
            "Context: last_rows_available="
            f"{has_data}. This flag only indicates whether recent data rows exist; "
            "it should NOT override the keyword rule above. Unless the user explicitly "
            "asks for a chart/graph/visualization, continue to favor metrics_agent."
            " When the request clearly requires multiple actions (e.g., run a query"
            " and then visualize it), call the planner so it can orchestrate steps."
        )
    )

    system_prompt = SystemMessage(
        content="""You are a routing agent for an observability system.

CRITICAL RULES:
- If user explicitly mentions "chart", "graph", "visualize", or "plot"
  → If data rows already exist (last_rows_available=True), choose chart_agent.
  → If NO recent data exists, route to planner so it can fetch data then visualize.
- Use planner whenever the user clearly asks for multiple actions or you are unsure which agent should go first.
- Otherwise → choose metrics_agent for straightforward data questions.

Available agents:

1. **planner**: For multi-step/ambiguous requests. Produces a plan that the system will execute.
2. **metrics_agent**: For data queries (DEFAULT)
   - Use for analytics, listing data, SQL queries
   - This is your default choice for simple requests without visualization asks
3. **chart_agent**: For visualization requests ONLY
   - Use when user explicitly wants charts/graphs and data already exists

Return your decision with reasoning."""
    )

    llm_with_structure = llm.with_structured_output(RoutingDecision)
    messages = [context_hint, system_prompt] + state["messages"]

    try:
        decision = llm_with_structure.invoke(messages)
        print(f"🧭 Routing (LLM): {decision.agent} - {decision.reasoning}")
        return decision.agent
    except Exception as exc:
        print(f"⚠️  Routing error: {exc}, defaulting to metrics_agent")
        return "metrics_agent"


def route_from_user_message(state: ObsState, llm) -> tuple[AgentName, Optional[AIMessage]]:
    """
    Route initial user message across diagnostics/planner/metrics/chart agents.
    Returns tuple of (agent_name, optional_refusal_message).
    """
    last_user_msg = _extract_last_user_message(state)
    if not last_user_msg:
        print("⚠️  No user message found, defaulting to metrics_agent")
        return "metrics_agent", None

    user_text = last_user_msg.content if isinstance(last_user_msg.content, str) else ""
    if not user_text:
        return "metrics_agent", None

    if _is_disallowed_request(user_text):
        print("🚫 Router: Disallowed request detected, refusing")
        return "complete", AIMessage(content=REFUSAL_MESSAGE)

    if not _is_analytics_request(user_text):
        print("🚫 Router: Irrelevant request detected, refusing")
        return "complete", AIMessage(content=REFUSAL_MESSAGE)

    if _enter_diagnostics_mode(state, user_text):
        return "planner", None

    return _route_default_flow(state, llm, user_text), None


def router_agent_node(state: ObsState, llm) -> ObsState:
    """
    LLM-based router agent that intelligently determines which agent to use.
    """
    # Check if previous agent encountered a fatal error
    if state.get("has_error", False):
        print("⚠️  Fatal error detected, stopping execution")
        return agent_state_update(
            state,
            messages=[],
            active_agent="complete",
            plan=[],
            plan_step_index=0,
            plan_mode="default",
        )

    plan_steps = state.get("plan", []) or []
    step_index = state.get("plan_step_index", 0)
    refusal_message = None

    if plan_steps and step_index < len(plan_steps):
        step = plan_steps[step_index]
        agent_name = step.get("agent", "metrics_agent")
        objective = step.get("objective", "")
        print(
            f"🧭 Planner routing: step {step_index + 1}/{len(plan_steps)} → {agent_name}"
            + (f" ({objective})" if objective else "")
        )
    elif plan_steps and step_index >= len(plan_steps):
        return agent_state_update(
            state,
            messages=[],
            active_agent="complete",
            plan=[],
            plan_step_index=0,
            plan_mode="default",
        )
    elif not plan_steps and step_index > 0:
        return agent_state_update(
            state,
            messages=[],
            active_agent="complete",
            plan=[],
            plan_step_index=0,
            plan_mode="default",
        )
    else:
        agent_name, refusal_message = route_from_user_message(state, llm)
        plan_steps = state.get("plan", []) or []
        step_index = state.get("plan_step_index", 0)

    return agent_state_update(
        state,
        messages=[refusal_message] if refusal_message else [],
        active_agent=agent_name,
        plan=plan_steps,
        plan_step_index=step_index,
    )
