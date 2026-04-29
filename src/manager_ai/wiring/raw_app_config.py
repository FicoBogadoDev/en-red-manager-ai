from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

from manager_ai.adapters.llm.text_generation.wiring import TextGenerationLLMConfig
from manager_ai.adapters.qualification.config import HeuristicQualificationConfig
from manager_ai.wiring.settings import (
    ExtractorConfig,
    HeuristicMessageClassifierConfig,
    HeuristicStructuredExtractionConfig,
    MessageClassifierConfig,
    MessagingConfig,
    NoTrackingConfig,
    RegexExtractorConfig,
    StorageConfig,
    StructuredExtractionConfig,
    TrackingConfig,
)


class RawRulesReplyGenerationConfig(BaseModel):
    type: Literal["rules"]


class RawLLMReplyGenerationConfig(BaseModel):
    type: Literal["llm"]
    llm: TextGenerationLLMConfig


class RawSharedLLMReplyGenerationConfig(BaseModel):
    type: Literal["shared_llm"]
    shared: str


RawReplyGenerationConfig = Annotated[
    Union[
        RawRulesReplyGenerationConfig,
        RawLLMReplyGenerationConfig,
        RawSharedLLMReplyGenerationConfig,
    ],
    Field(discriminator="type"),
]


class RawLLMQualificationConfig(BaseModel):
    type: Literal["llm"]
    llm: TextGenerationLLMConfig


class RawSharedLLMQualificationConfig(BaseModel):
    type: Literal["shared_llm"]
    shared: str


RawQualificationConfig = Annotated[
    Union[
        HeuristicQualificationConfig,
        RawLLMQualificationConfig,
        RawSharedLLMQualificationConfig,
    ],
    Field(discriminator="type"),
]


class RawAppConfig(BaseModel):
    llm: TextGenerationLLMConfig
    messaging: MessagingConfig
    storage: StorageConfig
    extractor: ExtractorConfig = RegexExtractorConfig(type="regex")
    message_classifier: MessageClassifierConfig = HeuristicMessageClassifierConfig(type="heuristic")
    qualification: RawQualificationConfig = HeuristicQualificationConfig(type="heuristic")
    structured_extraction: StructuredExtractionConfig = HeuristicStructuredExtractionConfig(type="heuristic")
    reply_generation: RawReplyGenerationConfig = RawRulesReplyGenerationConfig(type="rules")
    tracking: TrackingConfig = NoTrackingConfig(type="off")
