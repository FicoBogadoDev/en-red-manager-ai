"""Qualification adapter config and construction.

To add a qualification strategy:
1. Implement QualificationPort.
2. Add a config model to this module.
3. Add a branch in build_qualification().
"""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

from manager_ai.adapters.llm.text_generation.wiring import (
    TextGenerationLLMConfig,
    build_llm,
)
from manager_ai.adapters.qualification.catalog import (
    DEFAULT_SERVICE_CATALOG_PATH,
    load_service_catalog,
)
from manager_ai.ports.qualification import QualificationPort


class HeuristicQualificationConfig(BaseModel):
    type: Literal["heuristic"]
    catalog_path: str = DEFAULT_SERVICE_CATALOG_PATH


class LLMQualificationConfig(BaseModel):
    type: Literal["llm"]
    llm: TextGenerationLLMConfig
    catalog_path: str = DEFAULT_SERVICE_CATALOG_PATH


QualificationConfig = Annotated[
    Union[HeuristicQualificationConfig, LLMQualificationConfig],
    Field(discriminator="type"),
]


def build_qualification(cfg: QualificationConfig) -> QualificationPort:
    catalog = load_service_catalog(cfg.catalog_path)
    match cfg:
        case LLMQualificationConfig():
            from manager_ai.adapters.qualification.llm import LLMQualificationAdapter

            return LLMQualificationAdapter(llm=build_llm(cfg.llm), catalog=catalog)
        case HeuristicQualificationConfig():
            from manager_ai.adapters.qualification.heuristic import (
                HeuristicQualificationAdapter,
            )

            return HeuristicQualificationAdapter(catalog=catalog)
