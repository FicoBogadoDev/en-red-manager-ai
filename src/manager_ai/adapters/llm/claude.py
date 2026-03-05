import os

import anthropic

from manager_ai.models.conversation import Message


class ClaudeAdapter:
    def __init__(self, model: str, api_key_env: str) -> None:
        api_key = os.environ.get(api_key_env)
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def complete(self, messages: list[Message]) -> str:
        # Separate system prompt from conversation history
        system_messages = [m for m in messages if m.role == "system"]
        conversation = [m for m in messages if m.role != "system"]

        system_text = system_messages[0].content if system_messages else ""

        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=system_text,
            messages=[{"role": m.role, "content": m.content} for m in conversation],
        )
        return response.content[0].text
