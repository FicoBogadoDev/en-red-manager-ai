import os

from pydantic_ai import Agent as PydanticAgent
from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, UserPromptPart

from manager_ai.adapters.llm._runner import run_coro_sync
from manager_ai.models.conversation import Message


class PydanticAIAdapter:
    """
    LLMPort implementation backed by PydanticAI with the Anthropic provider.

    Creates a stateless PydanticAgent per complete() call, passing the system
    prompt as instructions= and the conversation history as message_history=.
    output_type=str makes this a direct drop-in replacement for ClaudeAdapter.
    """

    def __init__(self, model: str, api_key_env: str) -> None:
        api_key = os.environ.get(api_key_env)
        if api_key:
            os.environ["ANTHROPIC_API_KEY"] = api_key
        self._model_id = f"anthropic:{model}"

    def complete(self, messages: list[Message]) -> str:
        system_msgs = [m for m in messages if m.role == "system"]
        convo_msgs = [m for m in messages if m.role != "system"]

        system_text = system_msgs[0].content if system_msgs else ""

        if not convo_msgs:
            return ""

        *history_msgs, last_user = convo_msgs

        # Build PydanticAI message history from prior conversation turns.
        pydantic_history: list[ModelRequest | ModelResponse] = []
        for msg in history_msgs:
            if msg.role == "user":
                pydantic_history.append(
                    ModelRequest(parts=[UserPromptPart(content=msg.content)])
                )
            elif msg.role == "assistant":
                pydantic_history.append(
                    ModelResponse(parts=[TextPart(content=msg.content)])
                )

        # A new PydanticAgent per call is intentional: agents are stateless at
        # construction (no network I/O), and this avoids caching complexity when
        # the system prompt changes between qualification and collection stages.
        agent: PydanticAgent[None, str] = PydanticAgent(
            model=self._model_id,
            output_type=str,
            instructions=system_text,
        )

        result = run_coro_sync(
            agent.run(
                last_user.content,
                message_history=pydantic_history or None,
            )
        )
        return result.output
