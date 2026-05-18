from pathlib import Path
from typing import Any

from manager_ai.adapters.qualification.catalog import (
    CatalogBullet,
    ServiceCatalog,
    load_service_catalog,
    parse_service_catalog,
)
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
from manager_ai.ports.qualification import QualificationDecision, QualificationScopeStatus


class StubLLM:
    def __init__(self, response: str) -> None:
        self.response = response
        self.messages: list[Any] = []

    def complete(self, system_prompt: str, messages: Any) -> str:
        self.messages.append((system_prompt, messages))
        return self.response


def user_message(text: str) -> ConversationMessage:
    return ConversationMessage(role=MessageRole.USER, content=text)


def test_service_catalog_parses_markdown_sections(
    tmp_path: Path,
) -> None:
    catalog_path = tmp_path / "service-catalog.md"
    catalog_path.write_text(
        "\n".join(
            [
                "# Catalogo",
                "",
                "## Si ofrecemos",
                "",
                "- Servicio custom.",
                "",
                "## No ofrecemos, pero puede aparecer junto a una consulta valida",
                "",
                "- Extra custom. Respuesta: No hacemos extras custom.",
            ]
        ),
        encoding="utf-8",
    )

    catalog = load_service_catalog(catalog_path)

    assert "## Si ofrecemos" in catalog.raw_markdown
    assert catalog.offered[0].label == "Servicio custom"
    assert catalog.adjacent_unsupported[0].response == "No hacemos extras custom"


def test_service_catalog_ignores_free_text_outside_known_sections() -> None:
    catalog = parse_service_catalog("# Catalogo\n\nTexto libre.\n")

    assert catalog.raw_markdown.startswith("# Catalogo")
    assert catalog.offered == []
    assert catalog.adjacent_unsupported == []


def test_heuristic_qualification_uses_injected_catalog() -> None:
    catalog = ServiceCatalog(
        raw_markdown="## Si ofrecemos\n\n- Red custom.",
        offered=[CatalogBullet(text="Red custom")],
    )
    adapter = HeuristicQualificationAdapter(catalog=catalog)

    result = adapter.qualify(
        thread=ContactThreadState(phone="+1"),
        job=JobState(),
        message=user_message("hola, necesito una red custom"),
    )

    assert result.decision == QualificationDecision.SERVICE
    assert result.service_items[0].reply_label == "Red custom"


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
    assert result.unsupported_items[0].reply_label == "Redes de pesca"


def test_heuristic_qualification_reports_mixed_supported_and_unsupported_items() -> None:
    adapter = HeuristicQualificationAdapter()

    result = adapter.qualify(
        thread=ContactThreadState(phone="+1"),
        job=JobState(),
        message=user_message("Necesito red para balcon y tambien un mosquitero"),
    )

    assert result.decision == QualificationDecision.SERVICE
    assert result.service_items[0].scope_status == QualificationScopeStatus.IN_SCOPE
    assert result.unsupported_items[0].reply_label == "Mosquiteros"


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


def test_llm_qualification_parses_item_level_decision() -> None:
    llm = StubLLM(
        '{"decision":"service","reason":"Pedido mixto.",'
        '"service_items":[{"raw_text":"red para balcon","normalized_service":"balcony_safety_net",'
        '"scope_status":"in_scope","reply_label":"red de seguridad para balcon","rejection_phrase":null}],'
        '"unsupported_items":[{"raw_text":"mosquitero","normalized_service":"mosquito_screen",'
        '"scope_status":"adjacent_unsupported","reply_label":"mosquiteros",'
        '"rejection_phrase":"No instalamos mosquiteros."}],'
        '"unknown_items":[]}'
    )
    adapter = LLMQualificationAdapter(llm=llm)

    result = adapter.qualify(
        thread=ContactThreadState(phone="+1"),
        job=JobState(),
        message=user_message("Necesito red para balcon y mosquitero"),
    )

    assert result.decision == QualificationDecision.SERVICE
    assert result.service_items[0].normalized_service == "balcony_safety_net"
    assert result.unsupported_items[0].rejection_phrase == "No instalamos mosquiteros."


def test_llm_qualification_prompt_includes_catalog() -> None:
    llm = StubLLM('{"decision":"unclear","reason":"sin evidencia"}')
    adapter = LLMQualificationAdapter(llm=llm)

    adapter.qualify(
        thread=ContactThreadState(phone="+1"),
        job=JobState(),
        message=user_message("hola"),
    )

    system_prompt, _ = llm.messages[0]
    assert "## Si ofrecemos" in system_prompt
    assert "Mosquiteros. Respuesta: No instalamos mosquiteros." in system_prompt


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
