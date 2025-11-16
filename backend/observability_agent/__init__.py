"""
Observability Agent - Multi-agent system for observability analytics.

This package provides a modular multi-agent system for:
- Text2SQL analytics queries
- Row exploration and debugging
- Data visualization
"""

from .core.graph import build_graph
from .core.state import ObsState, AgentName
from .utils.runner import run_obs_agent

__all__ = [
    "build_graph",
    "ObsState",
    "AgentName",
    "run_obs_agent",
]

__version__ = "0.1.0"
