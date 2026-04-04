from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal, Union

import toml
from pydantic import BaseModel, Field

from manager_ai.adapters.llm.claude import ClaudeAdapter
from manager_ai.adapters.llm.log import LogLLMAdapter
from manager_ai.adapters.llm.pydantic_ai_adapter import PydanticAIAdapter
from manager_ai.adapters.messaging.log import LogMessagingAdapter
from manager_ai.adapters.quote_drafting.mock import MockQuoteDraftingAdapter
from manager_ai.adapters.reply_generation.llm import LLMConversationReplyAdapter
from manager_ai.adapters.reply_generation.rules import RulesConversationReplyAdapter
from manager_ai.adapters.reminder.mock import MockReminderAdapter
from manager_ai.adapters.scheduling.mock import MockSchedulingAdapter
from manager_ai.adapters.storage.json_file import JsonFileStorageAdapter
from manager_ai.adapters.storage.memory import InMemoryStorageAdapter
from manager_ai.agent.workflow_agent import Agent
from manager_ai.adapters.classifier.heuristic import HeuristicMessageClassifier
from manager_ai.adapters.classifier.llm import LLMMessageClassifier
from manager_ai.adapters.structured_extraction.heuristic import HeuristicStructuredExtractionAdapter
from manager_ai.adapters.structured_extraction.llm import LLMStructuredExtractionAdapter
from manager_ai.ports.llm import LLMPort
from manager_ai.ports.messaging import MessagingPort
from manager_ai.ports.conversation_repository import ConversationRepositoryPort
from manager_ai.ports.message_classifier import MessageClassifierPort
from manager_ai.ports.structured_extraction import StructuredExtractionPort
from manager_ai.ports.conversation_reply import ConversationReplyPort


# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Messaging
# ---------------------------------------------------------------------------

class LogMessagingConfig(BaseModel):
    type: Literal["log"]


MessagingConfig = Annotated[
    Union[LogMessagingConfig],
    Field(discriminator="type"),
]


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

class JsonStorageConfig(BaseModel):
    type: Literal["json"]
    path: str


class MemoryStorageConfig(BaseModel):
    type: Literal["memory"]


StorageConfig = Annotated[
    Union[JsonStorageConfig, MemoryStorageConfig],
    Field(discriminator="type"),
]


# ---------------------------------------------------------------------------
# Extractor
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Message Classifier
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Structured Extraction
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Reply Generation
# ---------------------------------------------------------------------------

class RulesReplyGenerationConfig(BaseModel):
    type: Literal["rules"]


class LLMReplyGenerationConfig(BaseModel):
    type: Literal["llm"]


ReplyGenerationConfig = Annotated[
    Union[RulesReplyGenerationConfig, LLMReplyGenerationConfig],
    Field(discriminator="type"),
]


# ---------------------------------------------------------------------------
# Tracking
# ---------------------------------------------------------------------------

class MLFlowTrackingConfig(BaseModel):
    type: Literal["mlflow"]
    experiment: str = "manager-ai"


class NoTrackingConfig(BaseModel):
    type: Literal["off"]


TrackingConfig = Annotated[
    Union[MLFlowTrackingConfig, NoTrackingConfig],
    Field(discriminator="type"),
]


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------

class AppConfig(BaseModel):
    llm: LLMConfig
    messaging: MessagingConfig
    storage: StorageConfig
    extractor: ExtractorConfig = RegexExtractorConfig(type="regex")
    message_classifier: MessageClassifierConfig = HeuristicMessageClassifierConfig(type="heuristic")
    structured_extraction: StructuredExtractionConfig = HeuristicStructuredExtractionConfig(type="heuristic")
    reply_generation: ReplyGenerationConfig = RulesReplyGenerationConfig(type="rules")
    tracking: TrackingConfig = NoTrackingConfig(type="off")


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def _build_llm(cfg: LLMConfig) -> LLMPort:
    if isinstance(cfg, PydanticAILLMConfig):
        return PydanticAIAdapter(model=cfg.model, api_key_env=cfg.api_key_env)
    if isinstance(cfg, ClaudeLLMConfig):
        return ClaudeAdapter(model=cfg.model, api_key_env=cfg.api_key_env)
    return LogLLMAdapter()


def _build_messaging(_cfg: MessagingConfig) -> MessagingPort:
    return LogMessagingAdapter()


def _build_storage(cfg: StorageConfig) -> ConversationRepositoryPort:
    if isinstance(cfg, JsonStorageConfig):
        return JsonFileStorageAdapter(directory=cfg.path)
    return InMemoryStorageAdapter()


def _build_extractor(cfg: ExtractorConfig):
    if isinstance(cfg, InstructorExtractorConfig):
        from manager_ai.adapters.extractor.instructor_extractor import InstructorExtractor
        return InstructorExtractor(model=cfg.model, api_key_env=cfg.api_key_env)
    return None


def _build_message_classifier(cfg: MessageClassifierConfig) -> MessageClassifierPort:
    if isinstance(cfg, LLMMessageClassifierConfig):
        return LLMMessageClassifier(model=cfg.model, api_key_env=cfg.api_key_env)
    return HeuristicMessageClassifier()


def _build_structured_extraction(cfg: StructuredExtractionConfig) -> StructuredExtractionPort:
    if isinstance(cfg, LLMStructuredExtractionConfigModel):
        return LLMStructuredExtractionAdapter(model=cfg.model, api_key_env=cfg.api_key_env)
    return HeuristicStructuredExtractionAdapter()


def _build_reply_generation(cfg: ReplyGenerationConfig, llm: LLMPort) -> ConversationReplyPort:
    if isinstance(cfg, LLMReplyGenerationConfig):
        return LLMConversationReplyAdapter(llm=llm)
    return RulesConversationReplyAdapter()


def build_agent(config_path: Path):
    raw = toml.loads(config_path.read_text(encoding="utf-8"))
    config = AppConfig.model_validate(raw)
    llm = _build_llm(config.llm)

    agent = Agent(
        llm=llm,
        messaging=_build_messaging(config.messaging),
        storage=_build_storage(config.storage),
        extractor=_build_extractor(config.extractor),
        classifier=_build_message_classifier(config.message_classifier),
        structured_extractor=_build_structured_extraction(config.structured_extraction),
        reply_generator=_build_reply_generation(config.reply_generation, llm),
        quote_drafter=MockQuoteDraftingAdapter(),
        scheduler=MockSchedulingAdapter(),
        reminders=MockReminderAdapter(),
    )

    if isinstance(config.tracking, MLFlowTrackingConfig):
        from manager_ai.agent.tracked_agent import MLFlowTrackedAgent
        return MLFlowTrackedAgent(agent=agent, experiment_name=config.tracking.experiment)

    return agent
