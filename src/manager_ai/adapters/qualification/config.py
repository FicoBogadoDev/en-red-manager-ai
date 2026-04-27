from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

from manager_ai.adapters.llm.config import LLMConfig


class HeuristicQualificationConfig(BaseModel):
    type: Literal["heuristic"]


class LLMQualificationConfig(BaseModel):
    type: Literal["llm"]
    llm: LLMConfig


QualificationConfig = Annotated[
    Union[HeuristicQualificationConfig, LLMQualificationConfig],
    Field(discriminator="type"),
]
