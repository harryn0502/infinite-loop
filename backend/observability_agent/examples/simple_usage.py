"""
Simple usage example showing the minimal code needed.
"""

from dotenv import load_dotenv
load_dotenv()

from observability_agent import build_graph, run_obs_agent
from observability_agent.holistic_ai_bedrock import get_chat_model

# Initialize once
llm = get_chat_model()
app = build_graph(llm)

# Run queries
#state = run_obs_agent("List the top 10 slowest runs", app)

# --- Example Scenarios -------------------------------------------------------
# 1) Follow-up question style multi-turn metrics analysis
#state = run_obs_agent("List the top 10 slowest success runs in agent_runs in last 24 hours", app)
#state = run_obs_agent("last 24 hrs", app, state)
#
# 2) Clarifier + diagnostics flow (table selection + refined follow-up)
# state = run_obs_agent("요즘 latency가 길어진 것 같은데 왜 그래?", app)
# # Router will first ask for the table name:
# state = run_obs_agent("call_model 기준으로 알려줘", app, state)
# # If more detail is needed, continue clarifying:
# state = run_obs_agent("최근 3일 전체 시스템 평균 latency", app, state)
#
# 3) Diagnostics mode (structured root cause analysis)
# state = run_obs_agent("최근 4시간 동안 토큰 사용량이 갑자기 늘었어. 이유 찾아줘", app)
# state = run_obs_agent("call_chain", app, state)
# (Planner will produce the diagnostics skeleton and run metrics/summary agents)
#
# 3-b) Diagnostics with tool-level follow-up
#state = run_obs_agent("최근 1일 동안 model 토큰이 급증한 원인을 알고 싶어", app)
#state = run_obs_agent("call_tool", app, state)
#
# 4) Tokens + chart
# state = run_obs_agent("Show total_tokens by agent for the last day", app)
# state = run_obs_agent("차트로 그려줘", app, state)

state = run_obs_agent("1+1 이 뭐야", app)
