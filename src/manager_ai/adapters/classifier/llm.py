from __future__ import annotations

import os

from pydantic import BaseModel, Field
from pydantic_ai import Agent as PydanticAgent
from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, UserPromptPart

from manager_ai.adapters.llm._runner import run_coro_sync
from manager_ai.models.conversation import ContactThreadState, ConversationMessage, IntentType, JobState
from manager_ai.ports.message_classifier import MessageClassifierPort


class _IntentClassification(BaseModel):
    intent: IntentType = Field(description="Intent principal del mensaje del cliente.")


def _history(thread: ContactThreadState, latest_message: ConversationMessage) -> list[ModelRequest | ModelResponse]:
    items: list[ModelRequest | ModelResponse] = []
    for message in thread.history[-8:]:
        if message.id == latest_message.id:
            continue
        if message.role.value == "user":
            items.append(ModelRequest(parts=[UserPromptPart(content=message.content)]))
        elif message.role.value == "assistant":
            items.append(ModelResponse(parts=[TextPart(content=message.content)]))
    return items


class LLMMessageClassifier(MessageClassifierPort):
    def __init__(self, model: str, api_key_env: str) -> None:
        api_key = os.environ.get(api_key_env)
        if api_key:
            os.environ["ANTHROPIC_API_KEY"] = api_key
        self._model_id = f"anthropic:{model}"

    def classify(
        self,
        thread: ContactThreadState,
        job: JobState | None,
        message: ConversationMessage,
    ) -> IntentType:
        agent: PydanticAgent[None, _IntentClassification] = PydanticAgent(
            model=self._model_id,
            output_type=_IntentClassification,
            instructions=(
                "Clasificá el último mensaje del cliente dentro de estas intenciones: "
                "new_inquiry, provide_evidence, quote_question, negotiation, scheduling, "
                "rescheduling, payment, post_install, follow_up, chit_chat, unknown. "
                "Pensá en conversaciones reales de En Red Rosario sobre redes de seguridad. "
                "Si el cliente comparte un nombre, dirección, medidas, fotos o cualquier dato útil del caso, "
                "eso cuenta como provide_evidence."
            ),
        )
        result = run_coro_sync(
            agent.run(
                message.content,
                message_history=_history(thread, message) or None,
            )
        )
        return result.output.intent
