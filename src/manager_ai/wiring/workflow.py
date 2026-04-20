from __future__ import annotations

from manager_ai.adapters.reply_generation.config import (
    LLMReplyGenerationConfig,
    ReplyGenerationConfig,
)
from manager_ai.ports.conversation_reply import ConversationReplyPort
from manager_ai.ports.message_classifier import MessageClassifierPort
from manager_ai.ports.structured_extraction import StructuredExtractionPort
from manager_ai.wiring.llm import build_llm
from manager_ai.wiring.settings import (
    ExtractorConfig,
    InstructorExtractorConfig,
    LLMMessageClassifierConfig,
    LLMStructuredExtractionConfigModel,
    MessageClassifierConfig,
    StructuredExtractionConfig,
)


def build_extractor(cfg: ExtractorConfig):
    if isinstance(cfg, InstructorExtractorConfig):
        from manager_ai.adapters.extractor.instructor_extractor import InstructorExtractor

        return InstructorExtractor(model=cfg.model, api_key_env=cfg.api_key_env)
    return None


def build_message_classifier(cfg: MessageClassifierConfig) -> MessageClassifierPort:
    if isinstance(cfg, LLMMessageClassifierConfig):
        from manager_ai.adapters.classifier.llm import LLMMessageClassifier

        return LLMMessageClassifier(model=cfg.model, api_key_env=cfg.api_key_env)
    from manager_ai.adapters.classifier.heuristic import HeuristicMessageClassifier

    return HeuristicMessageClassifier()


def build_structured_extraction(
    cfg: StructuredExtractionConfig,
) -> StructuredExtractionPort:
    if isinstance(cfg, LLMStructuredExtractionConfigModel):
        from manager_ai.adapters.structured_extraction.llm import (
            LLMStructuredExtractionAdapter,
        )

        return LLMStructuredExtractionAdapter(
            model=cfg.model,
            api_key_env=cfg.api_key_env,
        )
    from manager_ai.adapters.structured_extraction.heuristic import (
        HeuristicStructuredExtractionAdapter,
    )

    return HeuristicStructuredExtractionAdapter()


def build_reply_generation(
    cfg: ReplyGenerationConfig,
) -> ConversationReplyPort:
    from manager_ai.adapters.reply_generation.llm import LLMConversationReplyAdapter
    from manager_ai.adapters.reply_generation.rules import RulesConversationReplyAdapter

    if isinstance(cfg, LLMReplyGenerationConfig):
        return LLMConversationReplyAdapter(llm=build_llm(cfg.llm))

    return RulesConversationReplyAdapter()
