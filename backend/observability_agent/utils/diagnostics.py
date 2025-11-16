"""Shared helpers for diagnostics intent and configuration."""

import re
from typing import Any, Dict, List, Optional

DEFAULT_DIAGNOSTIC_WINDOW_HOURS = 24

_CAUSE_SIGNALS = [
    "why",
    "reason",
    "cause",
    "diagnostic",
    "root cause",
    "increase",
    "spike",
    "sudden",
    "slow",
    "unstable",
]

_METRIC_SIGNALS = [
    "latency",
    "response time",
    "delay",
    "tokens",
    "token",
    "token usage",
    "cost",
]

_LATENCY_KEYWORDS = ["latency", "delay", "slow", "response time"]
_TOKEN_KEYWORDS = ["token", "tokens", "token usage", "cost", "usage"]


def is_diagnostics_intent(text: str) -> bool:
    """Detect whether the user is asking for root-cause diagnostics."""
    if not text:
        return False
    lowered = text.lower()
    has_cause = any(sig in lowered for sig in _CAUSE_SIGNALS)
    has_metric = any(sig in lowered for sig in _METRIC_SIGNALS)
    return has_cause and has_metric


def infer_target_metric(text: str) -> str:
    """Guess which metric class (latency/tokens/both) is being referenced."""
    lowered = (text or "").lower()
    has_latency = any(keyword in lowered for keyword in _LATENCY_KEYWORDS)
    has_tokens = any(keyword in lowered for keyword in _TOKEN_KEYWORDS)
    if has_latency and has_tokens:
        return "both"
    if has_tokens:
        return "tokens"
    return "latency"


def extract_window_hours_from_text(text: str) -> Optional[int]:
    """Parse a timeframe like 'last 3 days' or 'last 24 hours'."""
    if not text:
        return None
    hour_match = re.search(r"(\d+)\s*(hour|hours)", text, re.IGNORECASE)
    if hour_match:
        return int(hour_match.group(1))
    day_match = re.search(r"(\d+)\s*(day|days)", text, re.IGNORECASE)
    if day_match:
        return int(day_match.group(1)) * 24
    return None


DIAGNOSTICS_STEP_SPECS: List[Dict[str, Any]] = [
    {
        "name": "overall_change",
        "agent": "metrics_agent",
        "mode": "overall",
        "objective_template": (
            "Compare the average/max {metric} between the recent {recent_hours} hours "
            "and the previous {baseline_hours} hours."
        ),
        "success": "Calculate average/max values and call counts for both periods and return as rows",
    },
    {
        "name": "by_tool",
        "agent": "metrics_agent",
        "mode": "by_tool",
        "objective_template": "Compare {metric} average and call count by tool for the two periods.",
        "success": "Find the top 10 tools with the largest increase.",
    },
    {
        "name": "by_agent",
        "agent": "metrics_agent",
        "mode": "by_agent",
        "objective_template": "Compare {metric} average and call count by agent_name.",
        "success": "Find agents with the largest increase.",
    },
    {
        "name": "summarize",
        "agent": "diagnostics_summary_agent",
        "objective_template": (
            "Summarize the key root cause candidates based on previous steps and suggest simple action items."
        ),
        "success": "Present 2-3 key causes with supporting numbers",
    },
]


SQL_GOAL_TEMPLATES: Dict[str, str] = {
    "overall": (
        "Compare the average and maximum {metric} between the last {recent_hours} hours "
        "and the previous {baseline_hours} hours. Return one row per window_label "
        "with columns: window_label, avg_value, max_value, call_count."
    ),
    "by_tool": (
        "For the same two {recent_hours}h vs {baseline_hours}h windows, group by tool_name and compute "
        "{metric} average and call_count. Return top 10 tools with the largest increase in average {metric}."
    ),
    "by_agent": (
        "For the same two windows, group by agent_name and compute average {metric} and call_count. "
        "Return agents with the largest increase."
    ),
}


def build_diagnostics_sql_goal(metric: str, mode: str, baseline_hours: int, recent_hours: int) -> str:
    template = SQL_GOAL_TEMPLATES.get(mode, "")
    return template.format(metric=metric, baseline_hours=baseline_hours, recent_hours=recent_hours)
