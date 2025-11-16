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
state = run_obs_agent("For chains where the prompt side stayed under about 2k tokens, which 5 runs burned the most completion tokens? I’d like to see the chain name, run_id, prompt tokens, completion tokens, and how long each run took.", app)
# state = run_obs_agent("List the top 10 slowest runs", app, state)
# state = run_obs_agent("Create a bar chart from this data", app, state)
