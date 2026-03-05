from typing import Protocol

from manager_ai.models.conversation import Message


class LLMPort(Protocol):
    def complete(self, messages: list[Message]) -> str: ...
