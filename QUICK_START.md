# Quick Start Guide

## Installation

The package is located in `src/observability_agent/`. No installation needed - just import it.

## Minimal Example (3 lines)

```python
from observability_agent import build_graph, run_obs_agent
from tutorials.holistic_ai_bedrock import get_chat_model

# Initialize
llm = get_chat_model()
app = build_graph(llm)

# Run a query
state = run_obs_agent("Show me tools with high latency", app)
```

## Full Example

```python
from observability_agent import build_graph, run_obs_agent
from tutorials.holistic_ai_bedrock import get_chat_model

# Step 1: Get LLM and build graph
llm = get_chat_model()
app = build_graph(llm)

# Step 2: Run metrics query
state1 = run_obs_agent(
    "평균 latency가 가장 높은 tool 알려줘. 최근 7일 기준으로.",
    app
)

# Step 3: Continue conversation - list rows
state2 = run_obs_agent(
    "latency가 200ms 넘는 tool 호출 row 10개만 보여줘.",
    app,
    prev_state=state1
)

# Step 4: Replay a specific row
state3 = run_obs_agent(
    "두 번째 row 다시 replay해줘.",
    app,
    prev_state=state2
)

# Step 5: Create visualization
state4 = run_obs_agent(
    "지금 데이터로 tool별 평균 latency bar chart 그려줘.",
    app,
    prev_state=state2
)
```

## What Each Agent Does

### 1. Metrics Agent (default)
Handles analytics and Text2SQL queries.

**Examples:**
- "평균 latency가 가장 높은 tool 알려줘"
- "Show me the slowest 10 runs from last week"
- "What's the average token usage by agent?"

### 2. Row Agent
Lists specific data rows for exploration.

**Examples:**
- "latency가 200ms 넘는 row 보여줘"
- "List runs with errors"
- "Show me the last 20 tool calls"

### 3. Replay Agent
Re-runs previous agent executions.

**Examples:**
- "두 번째 row replay해줘"
- "Replay row 5"
- "Re-run the third one"

### 4. Chart Agent
Generates visualization specifications.

**Examples:**
- "bar chart 그려줘"
- "Create a line chart from this data"
- "Visualize as a scatter plot"

## Project Structure

```
infinite-loop/
├── src/observability_agent/     # Main package
│   ├── agents/                  # 4 agent implementations
│   ├── core/                    # State, routing, graph
│   ├── tools/                   # DB and API tools
│   └── utils/                   # Helpers
├── examples/                    # Usage examples
│   ├── observability_example.py # Full demo
│   └── simple_usage.py          # Minimal demo
├── tutorials/                   # Original notebooks
│   └── infinite_loop.ipynb      # Original code
├── MIGRATION_GUIDE.md           # Detailed migration docs
├── REFACTORING_SUMMARY.md       # What was refactored
└── QUICK_START.md               # This file
```

## Running Examples

```bash
# Run full example
python examples/observability_example.py

# Run simple example
python examples/simple_usage.py
```

## API Reference

### Main Functions

```python
# Build the agent graph
app = build_graph(llm)

# Run a query (starts new conversation)
state = run_obs_agent(user_message, app)

# Continue conversation
state = run_obs_agent(user_message, app, prev_state=state)
```

### State Structure

```python
ObsState = {
    "messages": List[AnyMessage],      # Conversation history
    "active_agent": str,               # Current agent name
    "last_rows": List[Dict[str, Any]]  # Recent query results
}
```

### Agent Names

- `"metrics_agent"` - Analytics/Text2SQL
- `"row_agent"` - Row exploration
- `"replay_agent"` - Run replay
- `"chart_agent"` - Visualization

## Customization

### Use Specific Agent Directly

```python
from observability_agent.agents import metrics_agent_node
from observability_agent.core import ObsState
from langchain_core.messages import HumanMessage

state: ObsState = {
    "messages": [HumanMessage(content="query")],
    "active_agent": "metrics_agent",
    "last_rows": [],
}

result = metrics_agent_node(state, llm)
```

### Replace Database Tool

Edit `src/observability_agent/tools/database.py`:

```python
import psycopg2

def run_sql(sql: str) -> Dict[str, Any]:
    # Your real DB implementation
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute(sql)
    # ...
```

### Enhance Routing

Edit `src/observability_agent/core/router.py` to use LLM-based routing instead of keywords.

## Troubleshooting

### Import Error
```python
# Add src to path if needed
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
```

### LLM Not Found
```python
# Make sure holistic_ai_bedrock is available
from tutorials.holistic_ai_bedrock import get_chat_model
llm = get_chat_model()
```

### State Not Persisting
```python
# Always pass prev_state for multi-turn
state1 = run_obs_agent("query 1", app)
state2 = run_obs_agent("query 2", app, prev_state=state1)  # Important!
```

## Documentation

- **Package README**: `src/observability_agent/README.md`
- **Migration Guide**: `MIGRATION_GUIDE.md`
- **Refactoring Summary**: `REFACTORING_SUMMARY.md`
- **Original Notebook**: `tutorials/infinite_loop.ipynb`

## Next Steps

1. Run the examples to verify everything works
2. Try your own queries
3. Replace stub tools with real implementations
4. Add your own custom agents
5. Enhance the routing logic

## Support

For questions or issues, refer to:
- The original notebook: `tutorials/infinite_loop.ipynb`
- Migration guide: `MIGRATION_GUIDE.md`
- Package source code in `src/observability_agent/`
