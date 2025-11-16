"""
Example usage of the observability agent system.

This demonstrates how to use the refactored modular structure.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.observability_agent import build_graph, run_obs_agent
from tutorials.holistic_ai_bedrock import get_chat_model


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
        "평균 latency가 가장 높은 tool 알려줘. 최근 7일 기준으로.",
        app
    )

    # Example 2: Row listing
    print("\n[Example 2] Row exploration")
    state2 = run_obs_agent(
        "latency가 200ms 넘는 tool 호출 row 10개만 보여줘.",
        app,
        prev_state=state1
    )

    # Example 3: Chart generation
    print("\n[Example 3] Chart visualization")
    state3 = run_obs_agent(
        "지금 데이터로 tool별 평균 latency bar chart 그려줘.",
        app,
        prev_state=state2
    )

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
