from __future__ import annotations

from pathlib import Path

import toml

from manager_ai.adapters.quote_drafting.mock import MockQuoteDraftingAdapter
from manager_ai.adapters.reminder.mock import MockReminderAdapter
from manager_ai.adapters.scheduling.mock import MockSchedulingAdapter
from manager_ai.agent.workflow_agent import Agent
from manager_ai.wiring.llm import build_llm
from manager_ai.wiring.messaging import build_messaging
from manager_ai.wiring.settings import AppConfig, MLFlowTrackingConfig
from manager_ai.wiring.storage import build_storage
from manager_ai.wiring.workflow import (
    build_extractor,
    build_message_classifier,
    build_reply_generation,
    build_structured_extraction,
)


def load_app_config(config_path: Path) -> AppConfig:
    raw = toml.loads(config_path.read_text(encoding="utf-8"))
    return AppConfig.model_validate(raw)


def build_agent(config_path: Path):
    config = load_app_config(config_path)
    llm = build_llm(config.llm)

    agent = Agent(
        llm=llm,
        messaging=build_messaging(config.messaging),
        storage=build_storage(config.storage),
        extractor=build_extractor(config.extractor),
        classifier=build_message_classifier(config.message_classifier),
        structured_extractor=build_structured_extraction(config.structured_extraction),
        reply_generator=build_reply_generation(config.reply_generation, llm),
        quote_drafter=MockQuoteDraftingAdapter(),
        scheduler=MockSchedulingAdapter(),
        reminders=MockReminderAdapter(),
    )

    if isinstance(config.tracking, MLFlowTrackingConfig):
        from manager_ai.agent.tracked_agent import MLFlowTrackedAgent

        return MLFlowTrackedAgent(agent=agent, experiment_name=config.tracking.experiment)

    return agent
