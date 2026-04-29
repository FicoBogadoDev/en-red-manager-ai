from typing import Protocol, TypeVar

from pydantic import BaseModel

from manager_ai.models.conversation import Message


StructuredOutputT = TypeVar("StructuredOutputT", bound=BaseModel)


class StructuredLLMPort(Protocol):
    def extract(
        self,
        system_prompt: str,
        messages: list[Message],
        output_type: type[StructuredOutputT],
    ) -> StructuredOutputT: ...
