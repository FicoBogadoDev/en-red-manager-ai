from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

from manager_ai.adapters.llm.text_generation.wiring import TextGenerationLLMConfig


class HeuristicQualificationConfig(BaseModel):
    type: Literal["heuristic"]


class LLMQualificationConfig(BaseModel):
    type: Literal["llm"]
    llm: TextGenerationLLMConfig


QualificationConfig = Annotated[
    Union[HeuristicQualificationConfig, LLMQualificationConfig],
    Field(discriminator="type"),
]
