from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

from manager_ai.adapters.llm.text_generation.config import LLMConfig


class RulesReplyGenerationConfig(BaseModel):
    type: Literal["rules"]


class LLMReplyGenerationConfig(BaseModel):
    type: Literal["llm"]
    llm: LLMConfig


ReplyGenerationConfig = Annotated[
    Union[RulesReplyGenerationConfig, LLMReplyGenerationConfig],
    Field(discriminator="type"),
]
