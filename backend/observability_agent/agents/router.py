"""Routing agent for the observability multi-agent system."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage

from ..core.state import ObsState, AgentName
from ..core.state_utils import agent_state_update
from ..utils.diagnostics import (
    DEFAULT_DIAGNOSTIC_WINDOW_HOURS,
    extract_window_from_hints,
    extract_window_hours_from_text,
    infer_target_metric,
    is_diagnostics_intent,
)

DEFAULT_FOLLOWUP = "조금 더 구체적으로 설명해 주실 수 있을까요?"
TABLE_NAMES = ("agent_runs", "call_model", "call_tool", "call_chain")
TABLE_SELECTION_PROMPT = (
    "어떤 테이블을 기준으로 분석할까요? "
    "agent_runs / call_model / call_tool / call_chain 중에서 선택해 주세요."
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
    "지연",
    "토큰",
    "token",
    "metric",
    "데이터",
    "run",
    "agent",
    "tool",
    "chart",
    "그래프",
    "observability",
]


class RoutingDecision(BaseModel):
    """LLM-based routing decision with reasoning."""

    agent: AgentName = Field(
        description="Agent to handle this request: planner, metrics_agent, or chart_agent"
    )
    reasoning: str = Field(
        description="Brief explanation of why this agent was chosen"
    )


class ClarificationDecision(BaseModel):
    """Structured output used to decide if a follow-up question is needed."""

    need_clarification: bool = Field(
        description="Is the user query too ambiguous to execute safely?"
    )
    reason: str = Field(description="Why it is or is not ambiguous.")
    followup_question: Optional[str] = Field(
        default=None,
        description="If clarification is needed, ask ONE concise question in the user's language.",
    )
    suggested_hints_schema: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured hints like metric/time_window to capture from the user.",
    )


CLARIFIER_SYSTEM_PROMPT = """
You are an intent clarifier for an observability Text2SQL agent.

Goal:
- If the user query is ambiguous for metrics/SQL, ask ONE concise follow-up question.
- If it's precise enough, set need_clarification=false.

Things that often need clarification:
- Time window (e.g., last 24h, last 3 days, last week)
- Scope (whole system vs a specific agent/tool/model)
- Metric (latency, input_tokens, output_tokens, total_tokens, cost)

Always respond as JSON compatible with ClarificationDecision.
Use the user's language (Korean vs English) for followup_question.
""".strip()


def _extract_last_user_message(state: ObsState) -> Optional[HumanMessage]:
    return next(
        (
            m
            for m in reversed(state.get("messages", []))
            if hasattr(m, "type") and m.type == "human" and isinstance(m, HumanMessage)
        ),
        None,
    )


def build_resolved_query(original: Optional[str], answer: str) -> str:
    original = (original or "").strip()
    answer = (answer or "").strip()
    if not original:
        return answer
    if not answer:
        return original
    return f"{original}\nClarified details: {answer}"


def decide_clarification(user_text: str, llm) -> ClarificationDecision:
    clarifier = llm.with_structured_output(ClarificationDecision)
    messages = [
        SystemMessage(content=CLARIFIER_SYSTEM_PROMPT),
        HumanMessage(content=user_text),
    ]
    return clarifier.invoke(messages)


def _enter_diagnostics_mode(
    state: ObsState,
    text: str,
    hints: Dict[str, Any],
) -> bool:
    if not is_diagnostics_intent(text):
        return False

    hint_hours = extract_window_from_hints(hints)
    detected_hours = extract_window_hours_from_text(text)
    window_hours = hint_hours or detected_hours or DEFAULT_DIAGNOSTIC_WINDOW_HOURS
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


def _mentions_allowed_table(text: str) -> bool:
    lowered = (text or "").lower()
    return any(name in lowered for name in TABLE_NAMES)


def _trigger_table_followup(state: ObsState, original_text: str) -> AgentName:
    state["clarification"] = {
        "status": "pending",
        "question": TABLE_SELECTION_PROMPT,
        "original_user_message": original_text,
        "resolved_query": None,
        "hints": {},
        "required_detail": "table_name",
    }
    print("🧭 Routing: clarifier_agent (table selection required)")
    return "clarifier_agent"


def _handle_pending_clarification(state: ObsState, user_text: str, llm) -> Optional[AgentName]:
    clar_state = state.get("clarification") or {"status": "none"}
    if clar_state.get("status") != "pending":
        return None

    if _is_disallowed_request(user_text):
        clar_state["status"] = "none"
        state["clarification"] = clar_state
        print("🧭 Routing: refusal_agent (disallowed request during clarification)")
        return "refusal_agent"

    if clar_state.get("required_detail") == "table_name" and not _mentions_allowed_table(user_text):
        clar_state["question"] = TABLE_SELECTION_PROMPT
        state["clarification"] = clar_state
        print("🧭 Routing: clarifier_agent (waiting for table selection answer)")
        return "clarifier_agent"

    resolved_query = build_resolved_query(
        clar_state.get("original_user_message"),
        user_text,
    )
    clar_state["resolved_query"] = resolved_query
    clar_state["status"] = "resolved"
    clar_state.pop("required_detail", None)
    state["clarification"] = clar_state
    print("🧭 Routing: received clarification response, continuing execution")
    if _enter_diagnostics_mode(state, resolved_query, clar_state.get("hints", {})):
        return "planner"
    return _route_default_flow(state, llm, resolved_query)


def _maybe_require_table_choice(state: ObsState, user_text: str) -> Optional[AgentName]:
    if not user_text or _mentions_allowed_table(user_text):
        return None
    return _trigger_table_followup(state, user_text)


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
        "그래프",
        "시각화",
        "차트",
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


def route_from_user_message(state: ObsState, llm) -> AgentName:
    """
    Combine clarification + diagnostics intent detection with the existing router flow.
    """
    last_user_msg = _extract_last_user_message(state)
    if not last_user_msg:
        print("⚠️  No user message found, defaulting to metrics_agent")
        return "metrics_agent"

    clar_state = state.get("clarification") or {"status": "none"}
    state["clarification"] = clar_state
    user_text = last_user_msg.content if isinstance(last_user_msg.content, str) else ""
    if not user_text:
        return "metrics_agent"

    if _is_disallowed_request(user_text):
        state["clarification"] = {"status": "none"}
        print("🧭 Routing: refusal_agent (disallowed request detected)")
        return "refusal_agent"

    if not _is_analytics_request(user_text):
        state["clarification"] = {"status": "none"}
        print("🧭 Routing: refusal_agent (irrelevant request detected)")
        return "refusal_agent"

    pending_decision = _handle_pending_clarification(state, user_text, llm)
    if pending_decision:
        return pending_decision

    table_decision = _maybe_require_table_choice(state, user_text)
    if table_decision:
        return table_decision

    try:
        decision = decide_clarification(user_text, llm)
    except Exception as exc:
        print(f"⚠️  Clarifier LLM error: {exc}, skipping clarification.")
        decision = ClarificationDecision(
            need_clarification=False,
            reason="LLM error",
            followup_question=None,
            suggested_hints_schema={},
        )

    if decision.need_clarification:
        question = decision.followup_question or DEFAULT_FOLLOWUP
        clar_state = {
            "status": "pending",
            "question": question,
            "original_user_message": user_text,
            "resolved_query": None,
            "hints": decision.suggested_hints_schema or {},
        }
        state["clarification"] = clar_state
        print("🧭 Routing: clarifier_agent (ambiguous user request)")
        return "clarifier_agent"

    clar_state = {
        "status": "none",
        "original_user_message": user_text,
        "resolved_query": None,
        "hints": decision.suggested_hints_schema or {},
    }
    state["clarification"] = clar_state

    if _enter_diagnostics_mode(state, user_text, clar_state.get("hints", {})):
        return "planner"

    return _route_default_flow(state, llm, user_text)


def router_agent_node(state: ObsState, llm) -> ObsState:
    """
    LLM-based router agent that intelligently determines which agent to use.
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
        agent_name = route_from_user_message(state, llm)
        plan_steps = state.get("plan", []) or []
        step_index = state.get("plan_step_index", 0)

    return agent_state_update(
        state,
        messages=[],
        active_agent=agent_name,
        plan=plan_steps,
        plan_step_index=step_index,
    )
