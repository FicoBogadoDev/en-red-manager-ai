from pathlib import Path
from typing import Any

import toml

from manager_ai.adapters.llm.claude import ClaudeAdapter
from manager_ai.adapters.llm.log import LogLLMAdapter
from manager_ai.adapters.messaging.log import LogMessagingAdapter
from manager_ai.adapters.storage.json_file import JsonFileStorageAdapter
from manager_ai.adapters.storage.memory import InMemoryStorageAdapter
from manager_ai.agent.agent import Agent
from manager_ai.ports.llm import LLMPort
from manager_ai.ports.messaging import MessagingPort
from manager_ai.ports.storage import StoragePort


def _build_llm(config: dict[str, Any]) -> LLMPort:
    adapter_name = config["adapters"]["llm"]
    if adapter_name == "claude":
        claude_cfg = config["claude"]
        return ClaudeAdapter(
            model=claude_cfg["model"],
            api_key_env=claude_cfg["api_key_env"],
        )
    if adapter_name == "log":
        return LogLLMAdapter()
    raise ValueError(f"Unknown LLM adapter: {adapter_name!r}")


def _build_messaging(config: dict[str, Any]) -> MessagingPort:
    adapter_name = config["adapters"]["messaging"]
    if adapter_name == "log":
        return LogMessagingAdapter()
    raise ValueError(f"Unknown messaging adapter: {adapter_name!r}")


def _build_storage(config: dict[str, Any]) -> StoragePort:
    adapter_name = config["adapters"]["storage"]
    if adapter_name == "json":
        json_cfg = config["json_storage"]
        return JsonFileStorageAdapter(directory=json_cfg["path"])
    if adapter_name == "memory":
        return InMemoryStorageAdapter()
    raise ValueError(f"Unknown storage adapter: {adapter_name!r}")


def build_agent(config_path: Path) -> Agent:
    config = toml.loads(config_path.read_text(encoding="utf-8"))
    return Agent(
        llm=_build_llm(config),
        messaging=_build_messaging(config),
        storage=_build_storage(config),
    )
