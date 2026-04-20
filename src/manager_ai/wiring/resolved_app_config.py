from __future__ import annotations

from pydantic import BaseModel

from manager_ai.adapters.llm.config import LLMConfig
from manager_ai.adapters.reply_generation.config import ReplyGenerationConfig
from manager_ai.wiring.settings import (
    ExtractorConfig,
    MessageClassifierConfig,
    MessagingConfig,
    StorageConfig,
    StructuredExtractionConfig,
    TrackingConfig,
)


class ResolvedAppConfig(BaseModel):
    llm: LLMConfig
    messaging: MessagingConfig
    storage: StorageConfig
    extractor: ExtractorConfig
    message_classifier: MessageClassifierConfig
    structured_extraction: StructuredExtractionConfig
    reply_generation: ReplyGenerationConfig
    tracking: TrackingConfig
