"""Routing agent for the observability multi-agent system."""

from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage

from ..core.state import ObsState, AgentName


class RoutingDecision(BaseModel):
    """LLM-based routing decision with reasoning."""

    agent: AgentName = Field(
        description="The agent to handle this request: 'metrics_agent' or 'chart_agent'"
    )
    reasoning: str = Field(
        description="Brief explanation of why this agent was chosen"
    )


def route_from_user_message(state: ObsState, llm) -> AgentName:
    """
    Hybrid routing: Keyword pre-check + LLM fallback.

    Strategy:
    1. Hard rules for explicit chart keywords
    2. LLM-based routing for ambiguous cases
    3. Context-aware (checks last_rows availability)

    Args:
        state: Current observability state with conversation history
        llm: Language model instance for routing decision

    Returns:
        Name of the agent to route to
    """
    # 1) Get last user message
    last_user_msg = next(
        (m for m in reversed(state["messages"]) if hasattr(m, 'type') and m.type == "human"),
        None
    )

    if not last_user_msg:
        print("⚠️  No user message found, defaulting to metrics_agent")
        return "metrics_agent"

    text = last_user_msg.content.lower()

    has_data = bool(state.get("last_rows"))

    # 2) HARD RULE: Chart keywords → chart_agent (no LLM needed)
    chart_keywords = [
        "chart", "graph", "plot", "visualize",
        "bar chart", "line chart", "pie chart",
        "그래프", "시각화", "차트"
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

    # 3) LLM fallback for ambiguous cases (decide if planner needed)
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
- If user explicitly mentions \"chart\", \"graph\", \"visualize\", or \"plot\"
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
    except Exception as e:
        print(f"⚠️  Routing error: {e}, defaulting to metrics_agent")
        return "metrics_agent"


def router_agent_node(state: ObsState, llm) -> ObsState:
    """
    LLM-based router agent that intelligently determines which agent to use.

    This agent uses an LLM to analyze the user's intent and select
    the most appropriate specialized agent. It doesn't add messages
    to the conversation, just sets the active_agent field.

    Args:
        state: Current observability state
        llm: Language model instance for routing decision

    Returns:
        Updated state with active_agent set
    """
    plan_steps = state.get("plan", []) or []
    step_index = state.get("plan_step_index", 0)

    if plan_steps and step_index < len(plan_steps):
        step = plan_steps[step_index]
        agent_name = step.get("agent", "metrics_agent")
        objective = step.get("objective", "")
        print(
            f"🧭 Planner routing: step {step_index + 1}/{len(plan_steps)} → {agent_name}"
            + (f" ({objective})" if objective else "")
        )
    elif plan_steps and step_index >= len(plan_steps):
        return {
            "messages": [],
            "active_agent": "complete",
            "last_rows": state.get("last_rows", []),
            "chart_context": state.get("chart_context", {"rows": state.get("last_rows", []), "metadata": {}}),
            "plan": [],
            "plan_step_index": 0,
        }
    elif not plan_steps and step_index > 0:
        # No remaining plan but downstream agent already bumped the index,
        # so we can terminate without spending another LLM call.
        return {
            "messages": [],
            "active_agent": "complete",
            "last_rows": state.get("last_rows", []),
            "chart_context": state.get("chart_context", {"rows": state.get("last_rows", []), "metadata": {}}),
            "plan": [],
            "plan_step_index": 0,
        }
    else:
        agent_name = route_from_user_message(state, llm)
        # Preserve the plan_step_index even when there is no explicit plan.
        # Other agents (like metrics) bump this index to signal completion back to
        # the router/graph. Resetting it to 0 caused the workflow to never reach END.
        plan_steps = state.get("plan", []) or []
        step_index = state.get("plan_step_index", 0)

    return {
        "messages": [],  # router 자체는 message 추가 안 함
        "active_agent": agent_name,
        "last_rows": state.get("last_rows", []),
        "chart_context": state.get("chart_context", {"rows": state.get("last_rows", []), "metadata": {}}),
        "plan": plan_steps,
        "plan_step_index": step_index,
    }
