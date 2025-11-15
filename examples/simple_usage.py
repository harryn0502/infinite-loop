"""
Simple usage example showing the minimal code needed.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from observability_agent import build_graph, run_obs_agent
from tutorials.holistic_ai_bedrock import get_chat_model


# Initialize once
llm = get_chat_model()
app = build_graph(llm)

# Run queries
state = run_obs_agent("Show me tools with high latency", app)
state = run_obs_agent("List the top 10 slowest runs", app, state)
state = run_obs_agent("Create a bar chart from this data", app, state)
