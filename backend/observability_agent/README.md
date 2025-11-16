# Observability Agent

A modular multi-agent system for observability analytics, built with LangGraph.

## Features

- **Planner Agent**: Breaks complex user objectives into actionable steps
- **Metrics Agent**: Text2SQL analytics for querying observability data
- **Chart Agent**: Generate visualization specifications from recent queries

## Architecture

```
observability_agent/
├── core/           # Planner, routing, and graph workflow
├── agents/         # Agent implementations (planner, metrics, chart)
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
    "Create a chart of those results",
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
- `planner.py`: Multi-step planning agent
- `metrics.py`: Text2SQL metrics agent
- `chart.py`: Visualization generation

### Tools (`tools/`)
- `schema.py`: Database schema definition
- `database.py`: SQL execution helper

### Utils (`utils/`)
- `sql_parser.py`: Extract SQL from LLM responses
- `runner.py`: Multi-turn conversation runner

## Extending the System

### Replace Stub Tools

The bundled SQLite helper is intentionally simple. Replace it with your production data source:

```python
# tools/database.py
import psycopg2

def run_sql(sql: str) -> Dict[str, Any]:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute(sql)
    # ... return results
```

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
