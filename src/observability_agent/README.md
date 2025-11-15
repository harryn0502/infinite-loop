# Observability Agent

A modular multi-agent system for observability analytics, built with LangGraph.

## Features

- **Metrics Agent**: Text2SQL analytics for querying observability data
- **Row Explorer Agent**: Browse and inspect specific data rows
- **Replay Agent**: Re-run previous agent executions
- **Chart Agent**: Generate visualization specifications

## Architecture

```
observability_agent/
├── core/           # State, routing, and graph workflow
├── agents/         # Agent implementations (metrics, row, replay, chart)
├── tools/          # Database and API integrations
└── utils/          # Helper utilities (SQL parsing, runner)
```

## Quick Start

```python
from observability_agent import build_graph, run_obs_agent
from tutorials.holistic_ai_bedrock import get_chat_model

# Initialize
llm = get_chat_model()
app = build_graph(llm)

# Run a query
state = run_obs_agent(
    "Show me the top 5 slowest tool calls from last week",
    app
)

# Continue conversation
state = run_obs_agent(
    "Replay the second row",
    app,
    prev_state=state
)
```

## Module Structure

### Core (`core/`)
- `state.py`: TypedDict state definitions
- `router.py`: Keyword-based routing logic
- `graph.py`: LangGraph workflow assembly

### Agents (`agents/`)
- `metrics.py`: Text2SQL metrics agent
- `row_explorer.py`: Row listing and exploration
- `replay.py`: Agent run replay
- `chart.py`: Visualization generation

### Tools (`tools/`)
- `schema.py`: Database schema definition
- `database.py`: SQL execution (stub)
- `replay_api.py`: Replay API integration (stub)

### Utils (`utils/`)
- `sql_parser.py`: Extract SQL from LLM responses
- `runner.py`: Multi-turn conversation runner

## Extending the System

### Replace Stub Tools

The database and replay tools are currently stubs. Replace them with real implementations:

```python
# tools/database.py
import psycopg2

def run_sql(sql: str) -> Dict[str, Any]:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute(sql)
    # ... return results
```

### Add New Agents

1. Create agent file in `agents/`
2. Add routing logic in `core/router.py`
3. Register in `core/graph.py`
4. Export from `agents/__init__.py`

### Enhance Routing

Replace keyword-based routing with LLM-based routing:

```python
# core/router.py
def route_from_user_message(state: ObsState) -> AgentName:
    routing_llm = get_chat_model()
    # Use LLM to classify intent
    # Return appropriate agent name
```

## Requirements

- langgraph
- langchain-core
- holistic_ai_bedrock (or compatible LLM provider)

## License

MIT
