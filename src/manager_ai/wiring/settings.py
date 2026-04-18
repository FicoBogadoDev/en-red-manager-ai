from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


class PydanticAILLMConfig(BaseModel):
    type: Literal["pydantic_ai"]
    model: str
    api_key_env: str


class ClaudeLLMConfig(BaseModel):
    type: Literal["claude"]
    model: str
    api_key_env: str


class LogLLMConfig(BaseModel):
    type: Literal["log"]


LLMConfig = Annotated[
    Union[PydanticAILLMConfig, ClaudeLLMConfig, LogLLMConfig],
    Field(discriminator="type"),
]


class LogMessagingConfig(BaseModel):
    type: Literal["log"]


MessagingConfig = Annotated[
    Union[LogMessagingConfig],
    Field(discriminator="type"),
]


class JsonStorageConfig(BaseModel):
    type: Literal["json"]
    path: str


class MemoryStorageConfig(BaseModel):
    type: Literal["memory"]


StorageConfig = Annotated[
    Union[JsonStorageConfig, MemoryStorageConfig],
    Field(discriminator="type"),
]


class InstructorExtractorConfig(BaseModel):
    type: Literal["instructor"]
    model: str
    api_key_env: str


class RegexExtractorConfig(BaseModel):
    type: Literal["regex"]


ExtractorConfig = Annotated[
    Union[InstructorExtractorConfig, RegexExtractorConfig],
    Field(discriminator="type"),
]


class HeuristicMessageClassifierConfig(BaseModel):
    type: Literal["heuristic"]


class LLMMessageClassifierConfig(BaseModel):
    type: Literal["llm"]
    model: str
    api_key_env: str


MessageClassifierConfig = Annotated[
    Union[HeuristicMessageClassifierConfig, LLMMessageClassifierConfig],
    Field(discriminator="type"),
]


class HeuristicStructuredExtractionConfig(BaseModel):
    type: Literal["heuristic"]


class LLMStructuredExtractionConfigModel(BaseModel):
    type: Literal["llm"]
    model: str
    api_key_env: str


StructuredExtractionConfig = Annotated[
    Union[HeuristicStructuredExtractionConfig, LLMStructuredExtractionConfigModel],
    Field(discriminator="type"),
]


class RulesReplyGenerationConfig(BaseModel):
    type: Literal["rules"]


class LLMReplyGenerationConfig(BaseModel):
    type: Literal["llm"]


ReplyGenerationConfig = Annotated[
    Union[RulesReplyGenerationConfig, LLMReplyGenerationConfig],
    Field(discriminator="type"),
]


class MLFlowTrackingConfig(BaseModel):
    type: Literal["mlflow"]
    experiment: str = "manager-ai"


class NoTrackingConfig(BaseModel):
    type: Literal["off"]


TrackingConfig = Annotated[
    Union[MLFlowTrackingConfig, NoTrackingConfig],
    Field(discriminator="type"),
]


class AppConfig(BaseModel):
    llm: LLMConfig
    messaging: MessagingConfig
    storage: StorageConfig
    extractor: ExtractorConfig = RegexExtractorConfig(type="regex")
    message_classifier: MessageClassifierConfig = HeuristicMessageClassifierConfig(type="heuristic")
    structured_extraction: StructuredExtractionConfig = HeuristicStructuredExtractionConfig(type="heuristic")
    reply_generation: ReplyGenerationConfig = RulesReplyGenerationConfig(type="rules")
    tracking: TrackingConfig = NoTrackingConfig(type="off")
