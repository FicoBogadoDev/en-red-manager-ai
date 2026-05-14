from typing import Any

from manager_ai.adapters.llm.text_generation.wiring import LogLLMConfig
from manager_ai.adapters.qualification.wiring import (
    HeuristicQualificationConfig,
    LLMQualificationConfig,
    build_qualification,
)
from manager_ai.adapters.qualification.heuristic import HeuristicQualificationAdapter
from manager_ai.adapters.qualification.llm import LLMQualificationAdapter
from manager_ai.models.conversation import (
    ContactThreadState,
    ConversationMessage,
    JobState,
    MessageRole,
)
from manager_ai.ports.qualification import QualificationDecision


class StubLLM:
    def __init__(self, response: str) -> None:
        self.response = response
        self.messages: list[Any] = []

    def complete(self, system_prompt: str, messages: Any) -> str:
        self.messages.append((system_prompt, messages))
        return self.response


def user_message(text: str) -> ConversationMessage:
    return ConversationMessage(role=MessageRole.USER, content=text)


def test_heuristic_qualification_treats_greeting_as_unclear() -> None:
    adapter = HeuristicQualificationAdapter()

    result = adapter.qualify(
        thread=ContactThreadState(phone="+1"),
        job=JobState(),
        message=user_message("hola"),
    )

    assert result.decision == QualificationDecision.UNCLEAR


def test_heuristic_qualification_rejects_explicit_non_service() -> None:
    adapter = HeuristicQualificationAdapter()

    result = adapter.qualify(
        thread=ContactThreadState(phone="+1"),
        job=JobState(),
        message=user_message("Hola, necesito una red de pesca"),
    )

    assert result.decision == QualificationDecision.NOT_SERVICE


def test_heuristic_qualification_keeps_known_service_job_on_chitchat() -> None:
    adapter = HeuristicQualificationAdapter()
    job = JobState()
    job.scope.installation_type = "balcony"

    result = adapter.qualify(
        thread=ContactThreadState(phone="+1"),
        job=job,
        message=user_message("jaja perfecto"),
    )

    assert result.decision == QualificationDecision.SERVICE


def test_llm_qualification_parses_structured_decision() -> None:
    llm = StubLLM(
        '{"decision":"unclear","reason":"Saludo inicial sin pedido concreto.","reply":"Hola! Es por redes de seguridad?"}'
    )
    adapter = LLMQualificationAdapter(llm=llm)

    result = adapter.qualify(
        thread=ContactThreadState(phone="+1"),
        job=JobState(),
        message=user_message("hola"),
    )

    assert result.decision == QualificationDecision.UNCLEAR
    assert result.reason == "Saludo inicial sin pedido concreto."
    assert result.reply == "Hola! Es por redes de seguridad?"


def test_llm_qualification_invalid_json_falls_back_to_unclear() -> None:
    adapter = LLMQualificationAdapter(llm=StubLLM("no-json"))

    result = adapter.qualify(
        thread=ContactThreadState(phone="+1"),
        job=JobState(),
        message=user_message("hola"),
    )

    assert result.decision == QualificationDecision.UNCLEAR


def test_build_qualification_constructs_heuristic_adapter() -> None:
    adapter = build_qualification(HeuristicQualificationConfig(type="heuristic"))

    assert isinstance(adapter, HeuristicQualificationAdapter)


def test_build_qualification_constructs_llm_adapter() -> None:
    adapter = build_qualification(
        LLMQualificationConfig(type="llm", llm=LogLLMConfig(type="log"))
    )

    assert isinstance(adapter, LLMQualificationAdapter)
