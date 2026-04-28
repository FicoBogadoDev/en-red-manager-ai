"""
Manual MLflow integration test for InstructorExtractor with real API calls.

Pre-seeds the conversation in COLLECTING stage so only the extractor is
called (one real API call). Verifies that the extractor.collect span is
written to MLflow with structured inputs and outputs.

mlflow.anthropic.autolog() intercepts the underlying Anthropic SDK call that
Instructor makes, so token usage and the real modified payload (with tool
schema injected by Instructor) will appear as a child span inside extractor.collect.

Usage:
    uv run python tests/integration/test_mlflow_instructor.py

Requires ANTHROPIC_API_KEY in .env (or already set in the environment).

Then inspect results in the MLflow UI:
    uv run mlflow ui --backend-store-uri sqlite:///mlflow.db
"""

import os

from dotenv import load_dotenv

from manager_ai.adapters.extractor.instructor_extractor import InstructorExtractor
from manager_ai.adapters.llm.text_generation.log import LogLLMAdapter
from manager_ai.adapters.messaging.log import LogMessagingAdapter
from manager_ai.adapters.storage.memory import InMemoryStorageAdapter
from manager_ai.agent.agent import Agent
from manager_ai.agent.tracked_agent import MLFlowTrackedAgent
from manager_ai.models.client import ClientChart
from manager_ai.models.conversation import ConversationStage, ConversationState, Message

EXPERIMENT = "mlflow-instructor-test"
TEST_PHONE = "+5491100000003"
TEST_MESSAGE = "Me llamo Juan Pérez, vivo en Av. Corrientes 1234, Buenos Aires"


def _seed_collecting_state(storage: InMemoryStorageAdapter) -> None:
    """Pre-seed a COLLECTING stage state so qualification is bypassed."""
    state = ConversationState(
        phone=TEST_PHONE,
        stage=ConversationStage.COLLECTING,
        client=ClientChart(phone=TEST_PHONE),
        history=[
            Message(role="user", content="Hola, quiero instalar paneles solares"),
            Message(role="assistant", content="Perfecto, ¿podés contarme más sobre tu proyecto?"),
        ],
    )
    storage.save(TEST_PHONE, state)


def main() -> None:
    load_dotenv()
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY environment variable is not set.")

    storage = InMemoryStorageAdapter()
    _seed_collecting_state(storage)

    agent = Agent(
        llm=LogLLMAdapter(),
        messaging=LogMessagingAdapter(),
        storage=storage,
        extractor=InstructorExtractor(
            model="claude-haiku-4-5-20251001",
            api_key_env="ANTHROPIC_API_KEY",
        ),
    )
    tracked = MLFlowTrackedAgent(agent, experiment_name=EXPERIMENT)

    print(f"Sending test message as {TEST_PHONE!r}...")
    tracked.handle_message(phone=TEST_PHONE, text=TEST_MESSAGE)
    print("Done.")
    print(f"\nCheck MLflow UI → experiment '{EXPERIMENT}'")
    print("  uv run mlflow ui --backend-store-uri sqlite:///mlflow.db")
    print("\nExpect to see:")
    print("  extractor.collect  — inputs (your messages) and outputs (reply + extracted fields)")
    print("  └─ anthropic child span — real payload with Instructor's tool schema, token usage")


if __name__ == "__main__":
    main()
