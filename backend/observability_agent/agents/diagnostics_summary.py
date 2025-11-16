"""Diagnostics summary agent that explains root causes."""

import json
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from ..core.state import ObsState
from ..core.state_utils import agent_state_update


def _format_row(row: dict) -> str:
    parts = [f"{key}={value}" for key, value in row.items()]
    return ", ".join(parts)


def format_diagnostics_results_for_prompt(results) -> str:
    if not results:
        return "No diagnostics result rows were produced."

    lines = []
    for result in results:
        name = result.get("name", "step")
        desc = result.get("description", "")
        rows = result.get("rows") or []
        lines.append(f"[{name}] {desc}")

        if not rows:
            lines.append("  - (no rows)")
            continue

        preview = rows[:10]
        for idx, row in enumerate(preview, start=1):
            if isinstance(row, dict):
                row_text = _format_row(row)
            else:
                row_text = json.dumps(row, ensure_ascii=False)
            lines.append(f"  {idx}. {row_text}")

        if len(rows) > len(preview):
            lines.append(f"  ... (+{len(rows) - len(preview)} more rows)")

    return "\n".join(lines)


def _last_user_message_text(state: ObsState) -> str:
    for message in reversed(state.get("messages", [])):
        if getattr(message, "type", "") == "human" and isinstance(message.content, str):
            return message.content
    return ""


def _should_use_korean(text: str) -> bool:
    return any("\uac00" <= ch <= "\ud7a3" for ch in text)


def diagnostics_summary_agent_node(state: ObsState, llm) -> ObsState:
    ctx = state.get("diagnostics_context", {})
    results = ctx.get("results", [])
    target_metric = ctx.get("target_metric", "latency")
    baseline_hours = ctx.get("baseline_window_hours", 24)
    recent_hours = ctx.get("recent_window_hours", 24)
    user_text = _last_user_message_text(state)
    use_korean = _should_use_korean(user_text)

    first_rows = results[0].get("rows") if results else []
    if not first_rows:
        content = (
            "The first diagnostic step (overall_change) had no data to compare, "
            "so additional steps were skipped.\n"
            "Please verify that calls exist in both the recent and baseline periods, then try again."
        )
        summary_msg = AIMessage(content=content)
        plan_index = state.get("plan_step_index", 0)
        new_ctx = ctx.copy()
        new_ctx["results"] = results
        return agent_state_update(
            state,
            messages=[summary_msg],
            active_agent="diagnostics_summary_agent",
            plan_step_index=plan_index + 1,
            diagnostics_context=new_ctx,
        )

    system_prompt = (
        "You are a performance diagnostics assistant for an LLM agent platform.\n"
        f"The user reported that their {target_metric} changed unexpectedly.\n\n"
        "You will be given analysis tables for overall change, by tool, and by agent.\n"
        "Your job:\n"
        "1) Decide whether there was a real change between the two windows "
        f"(recent={recent_hours}h vs baseline={baseline_hours}h)\n"
        "2) Identify the top 1-3 likely causes with numeric evidence\n"
        "3) Explain them in simple language\n"
        "4) Recommend concrete next steps (limit retries, optimize prompts, etc.)\n"
        "Always cite the key numbers you rely on. "
        "Respond in English."
    )

    context_text = format_diagnostics_results_for_prompt(results)
    user_prompt = (
        "Here are the diagnostics results:\n\n"
        f"{context_text}\n\n"
        f"Explain why {target_metric} likely changed.\n"
        "If the data shows no significant change, say so and suggest monitoring steps."
    )

    resp = llm.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
    )

    summary_msg = AIMessage(content=resp.content)
    plan_steps = state.get("plan", []) or []
    plan_index = state.get("plan_step_index", 0)

    # Reset diagnostics context so future runs start clean
    new_ctx = ctx.copy()
    new_ctx["results"] = results

    return agent_state_update(
        state,
        messages=[summary_msg],
        active_agent="diagnostics_summary_agent",
        plan_step_index=plan_index + 1,
        diagnostics_context=new_ctx,
    )
