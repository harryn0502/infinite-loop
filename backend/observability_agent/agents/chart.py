"""Chart/visualization agent for creating data visualizations."""

import json
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from ..core.state import ObsState
from ..core.state_utils import agent_state_update
from ..tools import prepare_chart_data_tool
from .schemas import ChartSpecResponse

MAX_METADATA_ROWS = 20


def chart_agent_node(state: ObsState, llm) -> ObsState:
    """
    Generate chart specification (JSON) based on recent SQL results (last_rows).

    Generates visualization specifications from data:
    1. Checks if data rows are available
    2. Uses LLM to determine appropriate chart type
    3. Returns JSON specification for frontend rendering

    Chart types supported: bar, line, scatter
    Output format: JSON with chartType, xField, yField, data

    Args:
        state: Current observability state with last_rows
        llm: Language model instance

    Returns:
        Updated state with chart specification
    """
    last_rows = state.get("last_rows", [])
    user_message = state["messages"][-1]
    plan_steps = state.get("plan", []) or []
    plan_index = state.get("plan_step_index", 0)
    planner_step = plan_steps[plan_index] if plan_steps and plan_index < len(plan_steps) else None
    planner_instruction = ""
    if planner_step:
        planner_instruction = (
            f"Planner objective: {planner_step.get('objective', '')}\n"
            f"Context: {planner_step.get('input_context', '')}\n"
            f"Success criteria: {planner_step.get('success_criteria', '')}"
        )

    if not last_rows:
        msg = AIMessage(
            content=(
                "I don't have any recent data rows to visualize. "
                "Please first ask me for some metrics or a table of rows, "
                "then I can turn that into a chart."
            )
        )
        return agent_state_update(
            state,
            messages=[msg],
            active_agent="chart_agent",
            plan=plan_steps,
            plan_step_index=plan_index + 1,
        )

    # Prepare chart data and metadata
    chart_meta = {}
    try:
        chart_ready = prepare_chart_data_tool.invoke({"rows": last_rows})
        prepared_rows = chart_ready["rows"]
        chart_meta = chart_ready.get("metadata", {})
    except Exception:
        prepared_rows = last_rows
        chart_meta = {}

    system = SystemMessage(
        content=(
            "You are a visualization agent.\n"
            "You will receive:\n"
            "1) The user's request for a chart.\n"
            "2) A list of data rows (JSON-like dicts).\n\n"
            "Return a structured response with:\n"
            "- chart_type: The type of chart (bar, line, scatter, pie, etc.)\n"
            "- x_field: The field name to use for x-axis\n"
            "- y_field: The field name to use for y-axis\n"
            "- data: The data rows to visualize (same as input)\n"
            "- reasoning: Brief explanation of why this chart type and fields were chosen"
        )
    )

    helper_content = (
        f"User request: {user_message.content}\n\n"
        f"Prepared data rows: {prepared_rows}\n\n"
        f"Chart metadata: {chart_meta}"
    )
    if planner_instruction:
        helper_content += f"\n\nPlanner guidance:\n{planner_instruction}"

    helper_user = HumanMessage(content=helper_content)

    llm_with_structure = llm.with_structured_output(ChartSpecResponse)
    chart_response = llm_with_structure.invoke([system, helper_user])

    # Create JSON spec for frontend
    chart_data = chart_response.data or prepared_rows
    reasoning_text = chart_response.reasoning or "Model did not provide a detailed explanation."
    label_field = chart_response.x_field or chart_meta.get("label_field", "label")
    value_field = chart_response.y_field or chart_meta.get("value_field", "value")
    chart_type = chart_response.chart_type or chart_meta.get("suggested_chart", "bar")
    chart_spec = {
        "chartType": chart_type,
        "xField": label_field,
        "yField": value_field,
        "data": chart_data
    }

    chart_metadata = {
        "agent": "chart_agent",
        "chart_spec": chart_spec,
        "rows_preview": chart_data[:MAX_METADATA_ROWS],
        "row_count": len(chart_data),
        "user_request": user_message.content,
        "source_metadata": chart_meta,
    }

    spec_msg = AIMessage(
        content=f"**Reasoning:** {reasoning_text}\n\n```json\n{json.dumps(chart_spec, indent=2)}\n```",
        additional_kwargs={
            "reasoning": reasoning_text,
            "chart_spec": chart_spec,
            "agent_metadata": chart_metadata,
        }
    )

    return agent_state_update(
        state,
        messages=[spec_msg],
        active_agent="chart_agent",
        plan=plan_steps,
        plan_step_index=plan_index + 1,
    )
