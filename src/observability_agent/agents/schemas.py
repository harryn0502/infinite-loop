"""Structured output schemas for all agents with reasoning fields."""

from typing import Any, Dict, List
from pydantic import BaseModel, Field
from ..core.state import AgentName


class MetricsSQLResponse(BaseModel):
    """Response from metrics agent SQL generation."""

    sql_query: str = Field(
        description="The generated SQL query to execute"
    )
    reasoning: str = Field(
        default="",
        description="Brief explanation of why this SQL query was chosen and what it does"
    )


class MetricsSummaryResponse(BaseModel):
    """Response from metrics agent result summarization."""

    summary: str = Field(
        description="Human-readable summary of the SQL query results"
    )
    reasoning: str = Field(
        default="",
        description="Brief explanation of how the results were interpreted and summarized"
    )


class ChartSpecResponse(BaseModel):
    """Response from chart agent with visualization specification."""

    chart_type: str = Field(
        description="Type of chart: 'bar', 'line', 'scatter', 'pie', etc."
    )
    x_field: str = Field(
        description="Field name for x-axis"
    )
    y_field: str = Field(
        description="Field name for y-axis"
    )
    data: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Data rows for the chart"
    )
    reasoning: str = Field(
        default="",
        description="Brief explanation of why this chart type and fields were chosen"
    )


class PlanStep(BaseModel):
    """Individual step in a planner's execution plan."""

    step_number: int = Field(
        description="1-based ordering of the step"
    )
    agent: AgentName = Field(
        description="Agent name to execute this step (metrics_agent, chart_agent, etc.)"
    )
    objective: str = Field(
        description="Goal of this step"
    )
    input_context: str = Field(
        description="Important context or data required for this step"
    )
    success_criteria: str = Field(
        description="What must be produced for this step to be considered successful"
    )


class PlannerResponse(BaseModel):
    """Planner output describing multi-step execution."""

    summary: str = Field(
        description="High-level description of the plan"
    )
    steps: List[PlanStep] = Field(
        description="Ordered list of steps to execute"
    )
