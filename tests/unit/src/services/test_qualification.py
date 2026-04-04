import pytest

pytest.skip("Legacy qualification tests replaced by workflow tests.", allow_module_level=True)

from manager_ai.models.client import ClientChart
from manager_ai.models.conversation import (
    ConversationStage,
    ConversationState,
    Message,
)
from manager_ai.services.qualification import is_qualified, run_qualification


class StubLLM:
    """LLM stub that returns a preset response."""

    def __init__(self, response: str) -> None:
        self._response = response

    def complete(self, messages: list[Message]) -> str:
        return self._response


def make_state(phone: str = "+5493411234567") -> ConversationState:
    return ConversationState(
        phone=phone,
        client=ClientChart(phone=phone),
    )


# ---------------------------------------------------------------------------
# is_qualified
# ---------------------------------------------------------------------------

class TestIsQualified:
    def test_returns_true_when_qualified_present(self) -> None:
        assert is_qualified("Claro que sí, podemos ayudarte. QUALIFIED") is True

    def test_returns_false_when_not_qualified_present(self) -> None:
        assert is_qualified("Lo sentimos, no es nuestro rubro. NOT_QUALIFIED") is False

    def test_returns_false_when_neither_keyword_present(self) -> None:
        assert is_qualified("Hola, ¿en qué puedo ayudarte?") is False

    def test_not_qualified_takes_precedence_over_qualified(self) -> None:
        # Edge case: both keywords somehow appear
        assert is_qualified("QUALIFIED NOT_QUALIFIED") is False


# ---------------------------------------------------------------------------
# run_qualification
# ---------------------------------------------------------------------------

class TestRunQualification:
    def test_qualified_lead_advances_to_collecting(self) -> None:
        llm = StubLLM("¡Perfecto! Instalamos redes exactamente para eso. QUALIFIED")
        state = make_state()

        new_state, reply = run_qualification(
            state=state,
            user_message="Necesito una red de seguridad para mi balcón.",
            llm=llm,
            system_prompt="<system>",
        )

        assert new_state.stage == ConversationStage.COLLECTING

    def test_unqualified_lead_sets_stage_to_done(self) -> None:
        llm = StubLLM("Lo sentimos, no trabajamos eso. NOT_QUALIFIED")
        state = make_state()

        new_state, reply = run_qualification(
            state=state,
            user_message="Quiero una red de pesca.",
            llm=llm,
            system_prompt="<system>",
        )

        assert new_state.stage == ConversationStage.DONE

    def test_reply_strips_keyword(self) -> None:
        llm = StubLLM("¡Podemos ayudarte! QUALIFIED")
        state = make_state()

        _, reply = run_qualification(
            state=state,
            user_message="Necesito una red para el balcón.",
            llm=llm,
            system_prompt="<system>",
        )

        assert "QUALIFIED" not in reply
        assert "NOT_QUALIFIED" not in reply

    def test_history_grows_with_user_and_assistant_messages(self) -> None:
        llm = StubLLM("Hola. QUALIFIED")
        state = make_state()

        new_state, _ = run_qualification(
            state=state,
            user_message="Hola, quiero una red.",
            llm=llm,
            system_prompt="<system>",
        )

        assert len(new_state.history) == 2
        assert new_state.history[0].role == "user"
        assert new_state.history[1].role == "assistant"
