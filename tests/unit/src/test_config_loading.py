from pathlib import Path

from manager_ai.config import build_agent
from manager_ai.wiring.app import load_app_config, load_raw_app_config


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_reference_config_parses() -> None:
    config_path = PROJECT_ROOT / "config" / "reference.toml"

    config = load_app_config(config_path)

    assert config.llm.type == "claude"
    assert config.messaging.type == "log"
    assert config.storage.type == "json"
    assert config.qualification.type == "heuristic"


def test_dev_no_api_builds_agent() -> None:
    config_path = PROJECT_ROOT / "config" / "dev-no-api.toml"

    agent = build_agent(config_path)

    assert agent is not None


def test_dev_ui_config_parses() -> None:
    config_path = PROJECT_ROOT / "config" / "dev-ui-llm.toml"

    raw_config = load_raw_app_config(config_path)
    config = load_app_config(config_path)

    assert config.message_classifier.type == "llm"
    assert config.structured_extraction.type == "llm"
    assert raw_config.reply_generation.type == "shared_llm"
    assert raw_config.reply_generation.shared == "llm"
    assert config.reply_generation.type == "llm"
    assert config.reply_generation.llm.type == "claude"
    assert config.qualification.type == "heuristic"


def test_reply_generation_can_use_local_child_llm(tmp_path: Path) -> None:
    config_path = tmp_path / "local-reply-generation.toml"
    config_path.write_text(
        "\n".join(
            [
                "[llm]",
                '\ttype = "log"',
                "",
                "[messaging]",
                '\ttype = "log"',
                "",
                "[storage]",
                '\ttype = "memory"',
                "",
                "[reply_generation]",
                '\ttype = "llm"',
                "",
                "[reply_generation.llm]",
                '\ttype = "log"',
                "",
            ]
        ),
        encoding="utf-8",
    )

    config = load_app_config(config_path)
    agent = build_agent(config_path)

    assert config.reply_generation.type == "llm"
    assert config.reply_generation.llm.type == "log"
    assert agent is not None


def test_qualification_can_use_shared_llm(tmp_path: Path) -> None:
    config_path = tmp_path / "shared-qualification.toml"
    config_path.write_text(
        "\n".join(
            [
                "[llm]",
                '\ttype = "log"',
                "",
                "[messaging]",
                '\ttype = "log"',
                "",
                "[storage]",
                '\ttype = "memory"',
                "",
                "[qualification]",
                '\ttype = "shared_llm"',
                '\tshared = "llm"',
                "",
            ]
        ),
        encoding="utf-8",
    )

    raw_config = load_raw_app_config(config_path)
    config = load_app_config(config_path)
    agent = build_agent(config_path)

    assert raw_config.qualification.type == "shared_llm"
    assert config.qualification.type == "llm"
    assert config.qualification.llm.type == "log"
    assert agent is not None


def test_qualification_can_use_local_child_llm(tmp_path: Path) -> None:
    config_path = tmp_path / "local-qualification.toml"
    config_path.write_text(
        "\n".join(
            [
                "[llm]",
                '\ttype = "log"',
                "",
                "[messaging]",
                '\ttype = "log"',
                "",
                "[storage]",
                '\ttype = "memory"',
                "",
                "[qualification]",
                '\ttype = "llm"',
                "",
                "[qualification.llm]",
                '\ttype = "log"',
                "",
            ]
        ),
        encoding="utf-8",
    )

    config = load_app_config(config_path)
    agent = build_agent(config_path)

    assert config.qualification.type == "llm"
    assert config.qualification.llm.type == "log"
    assert agent is not None
