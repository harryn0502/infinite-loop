"""Planner agent responsible for decomposing user goals into agent steps."""

from typing import List, Optional
from langchain_core.messages import AIMessage, SystemMessage

from ..core.state import ObsState
from .schemas import PlannerResponse, PlanStep


AVAILABLE_AGENTS = """
1. metrics_agent
   - Purpose: Text2SQL analytics, executes SQL via run_sql_tool, formats rows via prepare_chart_data_tool.
   - Tools: get_observability_schema_tool, run_sql_tool, prepare_chart_data_tool.
2. chart_agent
   - Purpose: Generate visualization specs from the most recent rows or chart context.
   - Tools: Relies on prepared chart data from metrics_agent.
""".strip()


def _format_plan_text(summary: str, steps: List[PlanStep]) -> str:
    lines: List[str] = [f"**Planner Summary:** {summary}", ""]
    if not steps:
        lines.append("(Planner did not return any steps. Falling back to default metrics_agent.)")
        return "\n".join(lines)

    lines.append("**Execution Plan:**")
    for step in steps:
        lines.append(
            f"{step.step_number}. [{step.agent}] {step.objective}\n"
            f"   - Input: {step.input_context}\n"
            f"   - Success: {step.success_criteria}"
        )
    return "\n".join(lines)


def _default_plan(state: Optional[ObsState] = None) -> List[dict]:
    """Fallback when LLM planner fails. Adds chart step if user asked for a chart."""

    needs_chart = False
    if state and state.get("messages"):
        last_human = next(
            (m for m in reversed(state["messages"]) if getattr(m, "type", "") == "human"),
            None,
        )
        if last_human and isinstance(last_human.content, str):
            lowered = last_human.content.lower()
            chart_keywords = [
                "chart",
                "graph",
                "visualize",
                "plot",
                "stacked",
                "line chart",
                "bar chart",
            ]
            needs_chart = any(keyword in lowered for keyword in chart_keywords)

    steps: List[dict] = [
        {
            "step_number": 1,
            "agent": "metrics_agent",
            "objective": "Retrieve or compute the data needed to answer the user's request.",
            "input_context": (
                "Read the latest user question, inspect the schema, and generate the necessary SQL."
            ),
            "success_criteria": "SQL executes successfully and rows are available for follow-up steps.",
        }
    ]

    if needs_chart:
        steps.append(
            {
                "step_number": 2,
                "agent": "chart_agent",
                "objective": "Visualize the most recent metrics output as requested by the user.",
                "input_context": "Use the last rows/chart context produced by the metrics agent to build the chart.",
                "success_criteria": "Chart specification reflects the user's visualization requirements.",
            }
        )

    return steps


def planner_agent_node(state: ObsState, llm) -> ObsState:
    """Create a plan describing which agents should run and in what order."""

    system = SystemMessage(
        content=(
            "You are a planning agent for an observability analytics assistant.\n"
            "Break the user's goal into clear steps using the available agents.\n"
            "Rules:\n"
            "- Only use these agents: metrics_agent, chart_agent.\n"
            "- metrics_agent already knows how to fetch schema, run SQL, and prepare chart data.\n"
            "- chart_agent relies on the latest rows/chart context produced by metrics_agent.\n"
            "- Always order steps logically (metrics before chart if data is needed).\n"
            "- Every step MUST include step_number, agent, objective, input_context, success_criteria.\n"
            "- step_number must start at 1 and increment by 1.\n"
            "- Be explicit: describe the precise data or chart requirements in the objective and context.\n\n"
            "Return JSON that matches this template exactly:\n"
            "{\n"
            "  \"summary\": \"High-level plan\",\n"
            "  \"steps\": [\n"
            "    {\n"
            "      \"step_number\": 1,\n"
            "      \"agent\": \"metrics_agent\",\n"
            "      \"objective\": \"What this step accomplishes\",\n"
            "      \"input_context\": \"Details the agent needs\",\n"
            "      \"success_criteria\": \"How we know the step succeeded\"\n"
            "    },\n"
            "    {\n"
            "      \"step_number\": 2,\n"
            "      \"agent\": \"chart_agent\",\n"
            "      \"objective\": \"Visualization goal\",\n"
            "      \"input_context\": \"Which fields to chart, formats, etc.\",\n"
            "      \"success_criteria\": \"Chart characteristics\"\n"
            "    }\n"
            "  ]\n"
            "}\n\n"
            "Available agents:\n"
            f"{AVAILABLE_AGENTS}"
        )
    )

    planner_llm = llm.with_structured_output(PlannerResponse)
    messages = [system] + state["messages"]

    try:
        response = planner_llm.invoke(messages)
        plan_steps = [step.model_dump() for step in response.steps]
        plan_text = _format_plan_text(response.summary, response.steps)
    except Exception as exc:
        plan_steps = _default_plan(state)
        plan_text = (
            "Planner encountered an error and is falling back to a default plan.\n"
            f"Error: {exc}\n\n"
            "Default plan:\n"
            + "\n".join(
                f"{step['step_number']}. [{step['agent']}] {step['objective']}"
                for step in plan_steps
            )
        )

    if not plan_steps:
        plan_steps = _default_plan(state)

    plan_message = AIMessage(
        content=plan_text,
        additional_kwargs={
            "reasoning": "Planner generated execution plan",
            "plan_steps": plan_steps,
        }
    )

    return {
        "messages": [plan_message],
        "active_agent": "planner",
        "last_rows": state.get("last_rows", []),
        "chart_context": state.get(
            "chart_context",
            {"rows": state.get("last_rows", []), "metadata": {}},
        ),
        "plan": plan_steps,
        "plan_step_index": 0,
    }
