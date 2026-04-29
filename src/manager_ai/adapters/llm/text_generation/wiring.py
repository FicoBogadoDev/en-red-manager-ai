"""Text-generation LLM contract, config, and construction.

To add a provider:
1. Implement LLMTextGenerationPort.
2. Add a config model to this module.
3. Add a branch in build_llm().
"""

import os
from typing import Annotated, Literal, Protocol, Union, cast

from pydantic import BaseModel, Field

from manager_ai.models.conversation import Message


class LLMTextGenerationPort(Protocol):
    def complete(
        self,
        system_prompt: str,
        messages: list[Message],
    ) -> str: ...


class ClaudeLLMConfig(BaseModel):
    type: Literal["claude"]
    model: str
    api_key_env: str


class LogLLMConfig(BaseModel):
    type: Literal["log"]


TextGenerationLLMConfig = Annotated[
    Union[ClaudeLLMConfig, LogLLMConfig],
    Field(discriminator="type"),
]


def build_llm(cfg: TextGenerationLLMConfig) -> LLMTextGenerationPort:
    if isinstance(cfg, ClaudeLLMConfig):
        import anthropic

        from manager_ai.adapters.llm.text_generation.claude import ClaudeAdapter, ClaudeClient

        client = anthropic.Anthropic(api_key=_required_env(cfg.api_key_env))
        return ClaudeAdapter(model=cfg.model, client=cast(ClaudeClient, client))
    from manager_ai.adapters.llm.text_generation.log import LogLLMAdapter

    return LogLLMAdapter()


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if value is None:
        raise EnvironmentError(f"{name} environment variable is not set.")
    return value
