"""
Manual MLflow integration test.

Runs a simulated conversation turn using LogLLMAdapter (no real API calls)
wrapped with MLFlowTrackedAgent, so you can verify that runs, spans, params,
and metrics are written to MLflow correctly.

Usage:
    uv run python tests/integration/test_mlflow_manual.py

Then open the MLflow UI to inspect the results:
    uv run mlflow ui --backend-store-uri sqlite:///mlflow.db
"""

from pathlib import Path

from manager_ai.adapters.llm.log import LogLLMAdapter
from manager_ai.adapters.messaging.log import LogMessagingAdapter
from manager_ai.adapters.storage.memory import InMemoryStorageAdapter
from manager_ai.agent.agent import Agent
from manager_ai.agent.tracked_agent import MLFlowTrackedAgent

EXPERIMENT = "mlflow-integration-test"
TEST_PHONE = "+5491100000001"
TEST_MESSAGE = "Hola, quiero instalar paneles solares en mi casa"


def main() -> None:
    agent = Agent(
        llm=LogLLMAdapter(),
        messaging=LogMessagingAdapter(),
        storage=InMemoryStorageAdapter(),
    )
    tracked = MLFlowTrackedAgent(agent, experiment_name=EXPERIMENT)

    print(f"Sending test message as {TEST_PHONE!r}...")
    tracked.handle_message(phone=TEST_PHONE, text=TEST_MESSAGE)
    print("Done.")
    print(f"\nCheck MLflow UI → experiment '{EXPERIMENT}'")
    print("  uv run mlflow ui --backend-store-uri sqlite:///mlflow.db")


if __name__ == "__main__":
    main()
