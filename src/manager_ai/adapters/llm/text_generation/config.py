from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


class ClaudeLLMConfig(BaseModel):
    type: Literal["claude"]
    model: str
    api_key_env: str


class LogLLMConfig(BaseModel):
    type: Literal["log"]


LLMConfig = Annotated[
    Union[ClaudeLLMConfig, LogLLMConfig],
    Field(discriminator="type"),
]
