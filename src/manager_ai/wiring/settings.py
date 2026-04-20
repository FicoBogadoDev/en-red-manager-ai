from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


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


class MLFlowTrackingConfig(BaseModel):
    type: Literal["mlflow"]
    experiment: str = "manager-ai"


class NoTrackingConfig(BaseModel):
    type: Literal["off"]


TrackingConfig = Annotated[
    Union[MLFlowTrackingConfig, NoTrackingConfig],
    Field(discriminator="type"),
]
