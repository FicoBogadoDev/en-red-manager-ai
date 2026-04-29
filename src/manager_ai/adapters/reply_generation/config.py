from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

from manager_ai.adapters.llm.text_generation.wiring import TextGenerationLLMConfig


class RulesReplyGenerationConfig(BaseModel):
    type: Literal["rules"]


class LLMReplyGenerationConfig(BaseModel):
    type: Literal["llm"]
    llm: TextGenerationLLMConfig


ReplyGenerationConfig = Annotated[
    Union[RulesReplyGenerationConfig, LLMReplyGenerationConfig],
    Field(discriminator="type"),
]
