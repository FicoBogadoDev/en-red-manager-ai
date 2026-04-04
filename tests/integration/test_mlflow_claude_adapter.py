"""
Manual MLflow integration test for ClaudeAdapter with real API calls.

Verifies that token usage, latency, and model metadata are captured
automatically via mlflow.anthropic.autolog() as child spans inside
the llm.complete span.

Usage:
    uv run python tests/integration/test_mlflow_claude_adapter.py

Requires ANTHROPIC_API_KEY in .env (or already set in the environment).

Then inspect results in the MLflow UI:
    uv run mlflow ui --backend-store-uri sqlite:///mlflow.db
"""

import os

from dotenv import load_dotenv

from manager_ai.adapters.llm.claude import ClaudeAdapter
from manager_ai.adapters.messaging.log import LogMessagingAdapter
from manager_ai.adapters.storage.memory import InMemoryStorageAdapter
from manager_ai.agent.agent import Agent
from manager_ai.agent.tracked_agent import MLFlowTrackedAgent

EXPERIMENT = "mlflow-claude-adapter-test"
TEST_PHONE = "+5491100000002"
TEST_MESSAGE = "Hola, quiero instalar paneles solares en mi casa"


def main() -> None:
    load_dotenv()
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY environment variable is not set.")

    agent = Agent(
        llm=ClaudeAdapter(model="claude-haiku-4-5-20251001", api_key_env="ANTHROPIC_API_KEY"),
        messaging=LogMessagingAdapter(),
        storage=InMemoryStorageAdapter(),
    )
    tracked = MLFlowTrackedAgent(agent, experiment_name=EXPERIMENT)

    print(f"Sending test message as {TEST_PHONE!r}...")
    tracked.handle_message(phone=TEST_PHONE, text=TEST_MESSAGE)
    print("Done.")
    print(f"\nCheck MLflow UI → experiment '{EXPERIMENT}'")
    print("  uv run mlflow ui --backend-store-uri sqlite:///mlflow.db")
    print("\nExpect to see token usage (input_tokens, output_tokens) in the")
    print("anthropic child span nested inside the llm.complete span.")


if __name__ == "__main__":
    main()
