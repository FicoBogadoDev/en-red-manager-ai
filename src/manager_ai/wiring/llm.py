from manager_ai.ports.llm import LLMPort
from manager_ai.wiring.settings import ClaudeLLMConfig, LLMConfig, PydanticAILLMConfig


def build_llm(cfg: LLMConfig) -> LLMPort:
    if isinstance(cfg, PydanticAILLMConfig):
        from manager_ai.adapters.llm.pydantic_ai_adapter import PydanticAIAdapter

        return PydanticAIAdapter(model=cfg.model, api_key_env=cfg.api_key_env)
    if isinstance(cfg, ClaudeLLMConfig):
        from manager_ai.adapters.llm.claude import ClaudeAdapter

        return ClaudeAdapter(model=cfg.model, api_key_env=cfg.api_key_env)
    from manager_ai.adapters.llm.log import LogLLMAdapter

    return LogLLMAdapter()
