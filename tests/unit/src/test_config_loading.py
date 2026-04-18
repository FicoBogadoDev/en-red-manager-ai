from pathlib import Path

from manager_ai.config import build_agent
from manager_ai.wiring.app import load_app_config


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_reference_config_parses() -> None:
    config_path = PROJECT_ROOT / "config" / "reference.toml"

    config = load_app_config(config_path)

    assert config.llm.type == "pydantic_ai"
    assert config.messaging.type == "log"
    assert config.storage.type == "json"


def test_dev_no_api_builds_agent() -> None:
    config_path = PROJECT_ROOT / "config" / "dev-no-api.toml"

    agent = build_agent(config_path)

    assert agent is not None


def test_dev_ui_config_parses() -> None:
    config_path = PROJECT_ROOT / "config" / "dev-ui-llm.toml"

    config = load_app_config(config_path)

    assert config.message_classifier.type == "llm"
    assert config.structured_extraction.type == "llm"
    assert config.reply_generation.type == "llm"
