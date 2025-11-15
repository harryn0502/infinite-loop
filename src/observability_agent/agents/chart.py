"""Chart/visualization agent for creating data visualizations."""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from ..core.state import ObsState


def chart_agent_node(state: ObsState, llm) -> ObsState:
    """
    최근 SQL 결과(last_rows)를 기반으로 차트 스펙(JSON)를 생성.

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

    if not last_rows:
        msg = AIMessage(
            content=(
                "I don't have any recent data rows to visualize. "
                "Please first ask me for some metrics or a table of rows, "
                "then I can turn that into a chart."
            )
        )
        return {
            "messages": [msg],
            "active_agent": "chart_agent",
            "last_rows": last_rows,
        }

    system = SystemMessage(
        content=(
            "You are a visualization agent.\n"
            "You will receive:\n"
            "1) The user's request for a chart.\n"
            "2) A list of data rows (JSON-like dicts).\n\n"
            "Your job:\n"
            "- Decide an appropriate chart type (bar, line, etc.).\n"
            "- Suggest xField and yField.\n"
            "- Output a JSON spec that a frontend can use to render the chart.\n"
            "- You MUST respond with a JSON object inside a ```json ... ``` block.\n"
            "The JSON spec must have at least:\n"
            """{\n"
            '  \"chartType\": \"bar\" | \"line\" | \"scatter\",\n'
            '  \"xField\": \"...\",\n'
            '  \"yField\": \"...\",\n'
            '  \"data\": [ {\"field1\": ..., \"field2\": ...}, ... ]\n"
            "}\n"""
        )
    )

    helper_user = HumanMessage(
        content=(
            f"User request: {user_message.content}\n\n"
            f"Data rows: {last_rows}"
        )
    )

    spec_msg = llm.invoke([system, helper_user])

    return {
        "messages": [spec_msg],
        "active_agent": "chart_agent",
        "last_rows": last_rows,
    }
