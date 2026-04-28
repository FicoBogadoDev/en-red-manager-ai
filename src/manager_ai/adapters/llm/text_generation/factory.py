import os

from manager_ai.adapters.llm.text_generation.config import ClaudeLLMConfig, LLMConfig
from manager_ai.ports.llm import LLMPort


def build_llm(cfg: LLMConfig) -> LLMPort:
    if isinstance(cfg, ClaudeLLMConfig):
        from manager_ai.adapters.llm.text_generation.claude import ClaudeAdapter

        return ClaudeAdapter(model=cfg.model, api_key=_required_env(cfg.api_key_env))
    from manager_ai.adapters.llm.text_generation.log import LogLLMAdapter

    return LogLLMAdapter()


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if value is None:
        raise EnvironmentError(f"{name} environment variable is not set.")
    return value
