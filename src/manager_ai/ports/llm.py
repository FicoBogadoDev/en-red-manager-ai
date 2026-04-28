from typing import Protocol, TypeVar

from pydantic import BaseModel

from manager_ai.models.conversation import Message


StructuredOutputT = TypeVar("StructuredOutputT", bound=BaseModel)


class LLMPort(Protocol):
    def complete(
        self, 
        system_prompt: str, 
        messages: list[Message]
    ) -> str: ...


class StructuredLLMPort(Protocol):
    def extract(
        self,
        system_prompt: str,
        messages: list[Message],
        output_type: type[StructuredOutputT],
    ) -> StructuredOutputT: ...
