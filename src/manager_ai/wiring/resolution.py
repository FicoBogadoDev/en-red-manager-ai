from __future__ import annotations

from manager_ai.adapters.llm.config import LLMConfig
from manager_ai.adapters.reply_generation.config import (
    LLMReplyGenerationConfig,
    ReplyGenerationConfig,
    RulesReplyGenerationConfig,
)
from manager_ai.wiring.raw_app_config import (
    RawAppConfig,
    RawLLMReplyGenerationConfig,
    RawReplyGenerationConfig,
    RawRulesReplyGenerationConfig,
    RawSharedLLMReplyGenerationConfig,
)
from manager_ai.wiring.resolved_app_config import ResolvedAppConfig


def resolve_reply_generation_config(
    cfg: RawReplyGenerationConfig,
    app_llm: LLMConfig,
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


def resolve_app_config(raw: RawAppConfig) -> ResolvedAppConfig:
    return ResolvedAppConfig(
        llm=raw.llm,
        messaging=raw.messaging,
        storage=raw.storage,
        extractor=raw.extractor,
        message_classifier=raw.message_classifier,
        structured_extraction=raw.structured_extraction,
        reply_generation=resolve_reply_generation_config(raw.reply_generation, raw.llm),
        tracking=raw.tracking,
    )
