"""
Simple usage example showing the minimal code needed.
"""

from dotenv import load_dotenv
load_dotenv()

from backend.observability_agent import build_graph, run_obs_agent
from backend.observability_agent.holistic_ai_bedrock import get_chat_model

# Initialize once
llm = get_chat_model()
app = build_graph(llm)

# Run queries
#state = run_obs_agent("List the top 10 slowest runs", app)

# --- Example Scenarios -------------------------------------------------------
# 1) Follow-up question style multi-turn metrics analysis
state = run_obs_agent("List the top 10 slowest success runs in agent_runs in last 24 hours", app)
#state = run_obs_agent("last 24 hrs", app, state)
#
# 2) Diagnostics follow-up (provide extra detail manually)
# state = run_obs_agent("Latency seems to have increased recently. Why is that?", app)
# state = run_obs_agent("Focus on the call_model table for the last 3 days", app, state)
#
# 3) Diagnostics mode (structured root cause analysis)
# state = run_obs_agent("Token usage suddenly increased in the last 4 hours. Find the reason", app)
# state = run_obs_agent("call_chain", app, state)
# (Planner will produce the diagnostics skeleton and run metrics/summary agents)
#
# 3-b) Diagnostics with tool-level follow-up
#state = run_obs_agent("I want to know why model tokens spiked in the last day", app)
#state = run_obs_agent("call_tool", app, state)
#
# 4) Tokens + chart
# state = run_obs_agent("Show total_tokens by agent for the last day", app)
# state = run_obs_agent("Draw it as a chart", app, state)

#state = run_obs_agent("What is 1+1", app)
