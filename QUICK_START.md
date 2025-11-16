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

# Step 4: Create visualization
state3 = run_obs_agent(
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

### 2. Chart Agent
Generates visualization specifications.

**Examples:**
- "bar chart 그려줘"
- "Create a line chart from this data"
- "Visualize as a scatter plot"

## Project Structure

```
infinite-loop/
├── src/observability_agent/     # Main package
│   ├── agents/                  # Agent implementations
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

---

## Agents & Tools Deep Dive

### Available Agents

| Agent | Responsibilities | Typical Trigger | Key Files |
| --- | --- | --- | --- |
| `router` | Reads the latest conversation state, applies keyword shortcuts, or defers to an LLM to decide which agent should act next. It also enforces planner-produced plans step-by-step and signals completion when no further actions are required. | Every turn begins and ends with the router. | `src/observability_agent/agents/router.py`, `src/observability_agent/core/graph.py` |
| `planner` | Produces a structured multi-step plan whenever the router detects multi-action requests (e.g., “query then chart”). Each step strictly includes `step_number`, `agent`, `objective`, `input_context`, and `success_criteria`. Falls back to a default metrics→chart plan if validation fails. | Chart keywords when no cached data exists, or any ambiguous multi-part ask. | `src/observability_agent/agents/planner.py`, `src/observability_agent/agents/schemas.py` |
| `metrics_agent` | Converts natural language to SQL, validates and repairs statements, runs them via `run_sql_tool`, and summarizes the result set. Stores rows + chart context for follow-up turns. | Default for analytics/text questions. | `src/observability_agent/agents/metrics.py` |
| `chart_agent` | Builds visualization specs (bar/line/scatter/etc.) from the latest rows or chart context. Lazily normalizes the data via `prepare_chart_data_tool` if metadata is missing. | Explicit chart requests once data exists or the planner schedules it. | `src/observability_agent/agents/chart.py` |

### Tooling Reference

| Tool | Description | Consumed By | Source |
| --- | --- | --- | --- |
| `get_observability_schema_tool` | Returns a formatted schema string with table descriptions, column listings (via `PRAGMA table_info`), latency formulas, JSON extraction tips, and query guidance. Cached per process. | Metrics agent (every SQL-generation call). | `src/observability_agent/tools/schema.py` |
| `run_sql_tool` | Executes read-only SQL against `backend/agent_debug_db.sqlite`, enforcing a `LIMIT`, capturing execution metadata, and returning `columns`, `rows`, and diagnostics. | Metrics agent during execution/repair loop. | `src/observability_agent/tools/database.py` |
| `prepare_chart_data_tool` | Normalizes arbitrary rows into `{"label", "value"}` pairs, infers candidate columns, caps row counts, and emits metadata (source columns, suggested chart). | Chart agent and any visualization follow-ups. | `src/observability_agent/tools/chart_formatter.py` |

> All tools are exported via `src/observability_agent/tools/__init__.py`, so pointing to a different database or chart formatter is just a matter of swapping implementations there.

### Execution Flow

1. **User Turn & State Seeding**  
   `run_obs_agent` seeds or extends `ObsState` with `messages`, `active_agent`, `last_rows`, `chart_context`, `plan`, and `plan_step_index`.

2. **Router Pass**  
   - Checks for chart keywords; when no cached data exists it deliberately routes to the planner instead of directly to `chart_agent`.  
   - When no hard rule matches it invokes the LLM router with hints (last_rows availability, current plan progress).  
   - After every agent finishes, LangGraph re-enters the router so `route_from_state` can continue the plan or exit at `END`.

3. **Planner (when invoked)**  
   - Uses `PlannerResponse` structured output to emit numbered steps.  
   - If the LLM response is invalid, `_default_plan` inserts at least a metrics step and, when the user asked for a visualization, appends a chart step.  
   - Planner output is logged as an AI message so users can audit the instructions driving the rest of the run.

4. **Metrics Agent**  
   - Prompts with the cached schema plus optional planner hints.  
   - Generates SQL via `MetricsSQLResponse`, validates for forbidden clauses/functions, runs the query via `run_sql_tool`, and retries with corrective feedback up to three times.  
   - Stores the resulting `row_dicts` in `last_rows`, emits a “SQL draft + reasoning” message, and then a human-friendly summary message derived from `MetricsSummaryResponse`.

5. **Chart Agent (optional)**  
   - Requires `last_rows` or an existing `chart_context`.  
   - If metadata is empty it runs `prepare_chart_data_tool` using the recent rows, then crafts a JSON chart spec describing chart type, fields, and data.  
   - Returns a single AI message containing reasoning plus the spec, which the UI can render.

6. **Router Completion**  
   - Once `plan_step_index` exceeds the number of steps (or no plan existed but at least one agent ran), router sets `active_agent="complete"` so LangGraph exits gracefully without another LLM call.

### State Hand-off Essentials

- `last_rows`: Raw dict rows from the most recent metrics query. Enables follow-up questions without rerunning SQL.  
- `chart_context`: Stores rows + metadata prepared for visualization. Metrics agent records raw rows; chart agent enriches metadata (label/value fields, chart_type).  
- `plan` / `plan_step_index`: Planner instructions the router enforces. Agents increment the index after finishing; router auto-completes once steps are exhausted.  
- `messages`: Managed via LangGraph’s `add_messages` reducer so every agent (router, planner, etc.) can reference the full conversation.

Armed with this table-top view, it’s easy to trace any run in LangSmith: router nodes show routing decisions, planner nodes list the structured plan, metrics nodes log SQL + summaries, and chart nodes reveal the JSON spec.

## Support

For questions or issues, refer to:
- The original notebook: `tutorials/infinite_loop.ipynb`
- Migration guide: `MIGRATION_GUIDE.md`
- Package source code in `src/observability_agent/`
