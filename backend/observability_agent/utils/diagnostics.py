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
    "느려",
    "원인",
    "이유",
    "갑자기",
    "불안정",
]

_METRIC_SIGNALS = [
    "latency",
    "response time",
    "지연",
    "tokens",
    "token",
    "토큰",
    "비용",
    "cost",
]

_LATENCY_KEYWORDS = ["latency", "지연", "느려", "delay", "응답속도"]
_TOKEN_KEYWORDS = ["token", "tokens", "토큰", "비용", "cost", "usage"]


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
    """Parse a timeframe like 'last 3 days' or '최근 24시간'."""
    if not text:
        return None
    hour_match = re.search(r"(\d+)\s*(시간|hour|hours)", text, re.IGNORECASE)
    if hour_match:
        return int(hour_match.group(1))
    day_match = re.search(r"(\d+)\s*(일|day|days)", text, re.IGNORECASE)
    if day_match:
        return int(day_match.group(1)) * 24
    return None


def extract_window_from_hints(hints: Dict[str, Any]) -> Optional[int]:
    """Read time window hints provided by the clarifier."""
    if not hints:
        return None
    for key in ("time_window_hours", "window_hours", "recent_window_hours"):
        value = hints.get(key)
        if isinstance(value, (int, float)):
            return int(value)
    return None


DIAGNOSTICS_STEP_SPECS: List[Dict[str, Any]] = [
    {
        "name": "overall_change",
        "agent": "metrics_agent",
        "mode": "overall",
        "objective_template": (
            "최근 {recent_hours}시간과 그 전 {baseline_hours}시간의 {metric} 평균/최댓값을 비교한다."
        ),
        "success": "두 기간의 평균/최댓값과 호출 수를 계산해 rows로 반환",
    },
    {
        "name": "by_tool",
        "agent": "metrics_agent",
        "mode": "by_tool",
        "objective_template": "tool별 {metric} 평균과 호출 수를 두 기간으로 비교한다.",
        "success": "증가폭이 큰 tool 상위 10개를 찾는다.",
    },
    {
        "name": "by_agent",
        "agent": "metrics_agent",
        "mode": "by_agent",
        "objective_template": "agent_name별 {metric} 평균과 호출 수를 비교한다.",
        "success": "증가폭이 큰 agent를 찾는다.",
    },
    {
        "name": "summarize",
        "agent": "diagnostics_summary_agent",
        "objective_template": (
            "이전 단계들의 결과를 바탕으로 주요 원인 후보를 요약하고 간단한 action item을 제안한다."
        ),
        "success": "주요 원인 2~3개와 근거 숫자를 함께 제시",
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
