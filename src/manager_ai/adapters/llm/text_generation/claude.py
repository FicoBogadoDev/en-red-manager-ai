from typing import Protocol

from anthropic.types import ContentBlock, Message as ClaudeMessage, MessageParam, TextBlock

from manager_ai.models.conversation import Message


class ClaudeMessagesClient(Protocol):
    def create(
        self,
        *,
        model: str,
        max_tokens: int,
        system: str,
        messages: list[MessageParam],
    ) -> ClaudeMessage: ...


class ClaudeClient(Protocol):
    messages: ClaudeMessagesClient


class ClaudeAdapter:
    def __init__(self, model: str, client: ClaudeClient) -> None:
        self._client = client
        self._model = model

    def complete(self, system_prompt: str, messages: list[Message]) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=system_prompt,
            messages=_to_anthropic_messages(messages),
        )
        return _response_text(response.content)


def _to_anthropic_messages(messages: list[Message]) -> list[MessageParam]:
    anthropic_messages: list[MessageParam] = []
    for message in messages:
        if message.role == "user":
            anthropic_messages.append({"role": "user", "content": message.content})
        elif message.role == "assistant":
            anthropic_messages.append(
                {"role": "assistant", "content": message.content}
            )
    return anthropic_messages


def _response_text(content: list[ContentBlock]) -> str:
    return "".join(block.text for block in content if isinstance(block, TextBlock))
