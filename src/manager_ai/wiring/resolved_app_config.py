from __future__ import annotations

from pydantic import BaseModel

from manager_ai.adapters.llm.text_generation.wiring import TextGenerationLLMConfig
from manager_ai.adapters.qualification.wiring import QualificationConfig
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
    llm: TextGenerationLLMConfig
    messaging: MessagingConfig
    storage: StorageConfig
    extractor: ExtractorConfig
    message_classifier: MessageClassifierConfig
    qualification: QualificationConfig
    structured_extraction: StructuredExtractionConfig
    reply_generation: ReplyGenerationConfig
    tracking: TrackingConfig
