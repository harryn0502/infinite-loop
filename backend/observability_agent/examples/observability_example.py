"""
Example usage of the observability agent system.

This demonstrates how to use the refactored modular structure.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from observability_agent import build_graph, run_obs_agent
from backend.observability_agent.holistic_ai_bedrock import get_chat_model


def main():
    """Run observability agent examples."""
    # Get LLM instance
    llm = get_chat_model()

    # Build the graph
    app = build_graph(llm)

    print("=" * 60)
    print("Observability Agent - Modular Example")
    print("=" * 60)

    # Example 1: Metrics / Text2SQL query
    print("\n[Example 1] Metrics query")
    state1 = run_obs_agent(
        "Tell me the tool with the highest average latency. Based on the last 7 days.",
        app
    )

    # Example 2: Row listing
    print("\n[Example 2] Row exploration")
    state2 = run_obs_agent(
        "Show me 10 tool call rows with latency over 200ms.",
        app,
        prev_state=state1
    )

    # Example 3: Chart generation
    print("\n[Example 3] Chart visualization")
    state3 = run_obs_agent(
        "Draw a bar chart of average latency by tool with the current data.",
        app,
        prev_state=state2
    )

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
