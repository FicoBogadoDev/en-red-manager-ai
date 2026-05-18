from __future__ import annotations

from manager_ai.adapters.llm.text_generation.wiring import TextGenerationLLMConfig
from manager_ai.adapters.qualification.wiring import (
    HeuristicQualificationConfig,
    LLMQualificationConfig,
    QualificationConfig,
)
from manager_ai.adapters.reply_generation.config import (
    LLMReplyGenerationConfig,
    ReplyGenerationConfig,
    RulesReplyGenerationConfig,
)
from manager_ai.wiring.raw_app_config import (
    RawAppConfig,
    RawLLMQualificationConfig,
    RawLLMReplyGenerationConfig,
    RawQualificationConfig,
    RawReplyGenerationConfig,
    RawRulesReplyGenerationConfig,
    RawSharedLLMQualificationConfig,
    RawSharedLLMReplyGenerationConfig,
)
from manager_ai.wiring.resolved_app_config import ResolvedAppConfig


def resolve_reply_generation_config(
    cfg: RawReplyGenerationConfig,
    app_llm: TextGenerationLLMConfig,
) -> ReplyGenerationConfig:
    if isinstance(cfg, RawRulesReplyGenerationConfig):
        return RulesReplyGenerationConfig(type="rules")
    if isinstance(cfg, RawLLMReplyGenerationConfig):
        return LLMReplyGenerationConfig(type="llm", llm=cfg.llm)
    if cfg.shared != "llm":
        raise ValueError(
            f"Unsupported shared LLM reference '{cfg.shared}'. "
            "This first slice only supports 'shared = \"llm\"'."
        )
    return LLMReplyGenerationConfig(type="llm", llm=app_llm)


def resolve_qualification_config(
    cfg: RawQualificationConfig,
    app_llm: TextGenerationLLMConfig,
) -> QualificationConfig:
    if isinstance(cfg, HeuristicQualificationConfig):
        return HeuristicQualificationConfig(
            type="heuristic",
            catalog_path=cfg.catalog_path,
        )
    if isinstance(cfg, RawLLMQualificationConfig):
        return LLMQualificationConfig(
            type="llm",
            llm=cfg.llm,
            catalog_path=cfg.catalog_path,
        )
    if cfg.shared != "llm":
        raise ValueError(
            f"Unsupported shared LLM reference '{cfg.shared}'. "
            "Qualification only supports 'shared = \"llm\"'."
        )
    return LLMQualificationConfig(
        type="llm",
        llm=app_llm,
        catalog_path=cfg.catalog_path,
    )


def resolve_app_config(raw: RawAppConfig) -> ResolvedAppConfig:
    return ResolvedAppConfig(
        llm=raw.llm,
        messaging=raw.messaging,
        storage=raw.storage,
        extractor=raw.extractor,
        message_classifier=raw.message_classifier,
        qualification=resolve_qualification_config(raw.qualification, raw.llm),
        structured_extraction=raw.structured_extraction,
        reply_generation=resolve_reply_generation_config(raw.reply_generation, raw.llm),
        tracking=raw.tracking,
    )
