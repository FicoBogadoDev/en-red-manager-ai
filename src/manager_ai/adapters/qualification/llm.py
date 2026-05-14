from __future__ import annotations

from pydantic import BaseModel, ValidationError

from manager_ai.models.conversation import ContactThreadState, ConversationMessage, JobState, Message
from manager_ai.adapters.llm.text_generation.wiring import LLMTextGenerationPort
from manager_ai.ports.qualification import (
    QualificationDecision,
    QualificationPort,
    ServiceQualification,
)


class _QualificationOutput(BaseModel):
    decision: QualificationDecision
    reason: str
    reply: str | None = None


def _recent_history(thread: ContactThreadState, latest_message: ConversationMessage) -> list[Message]:
    messages: list[Message] = []
    for item in thread.history[-8:]:
        if item.id == latest_message.id:
            continue
        messages.append(Message(role=item.role.value, content=item.content))
    return messages


class LLMQualificationAdapter:
    def __init__(self, llm: LLMTextGenerationPort) -> None:
        self._llm = llm

    def qualify(
        self,
        thread: ContactThreadState,
        job: JobState,
        message: ConversationMessage,
    ) -> ServiceQualification:
        response = self._llm.complete(
            self._system_prompt(job),
            self._messages(thread, message),
        ).strip()
        try:
            parsed = _QualificationOutput.model_validate_json(response)
        except ValidationError:
            return ServiceQualification(
                decision=QualificationDecision.UNCLEAR,
                reason="LLM qualification response was not valid JSON.",
            )
        return ServiceQualification(
            decision=parsed.decision,
            reason=parsed.reason,
            reply=parsed.reply,
        )

    def _system_prompt(self, job: JobState) -> str:
        return (
            "Sos el clasificador de calificacion de servicio de En Red Rosario. "
            "En Red instala redes de seguridad para chicos y mascotas en balcones, techos, "
            "terrazas y escaleras. Clasifica el ultimo mensaje del cliente como JSON estricto. "
            "Usa decision='service' solo si el cliente busca o ya venia hablando de ese servicio. "
            "Usa decision='not_service' solo si hay evidencia clara de que busca otro rubro, "
            "por ejemplo red de pesca, futbol, volley o red LAN. "
            "Usa decision='unclear' para saludos, chitchat, preguntas vagas o falta de informacion. "
            "Nunca trates informacion faltante como motivo de descarte. "
            "Si el trabajo actual ya tiene tipo de instalacion o intencion de servicio, mantenelo como service "
            "aunque el ultimo mensaje sea casual. "
            "Devolve exactamente este JSON: "
            '{"decision":"service|not_service|unclear","reason":"...","reply":null}. '
            "reply puede ser una respuesta breve en espanol rioplatense cuando decision sea unclear o not_service.\n\n"
            f"Trabajo actual: estado={job.status.value}, "
            f"service_intent={job.scope.service_intent}, "
            f"installation_type={job.scope.installation_type}, "
            f"area_context={job.scope.area_context}, "
            f"missing_fields={', '.join(job.missing_fields) if job.missing_fields else 'ninguno'}."
        )

    def _messages(
        self,
        thread: ContactThreadState,
        message: ConversationMessage,
    ) -> list[Message]:
        return [
            *_recent_history(thread, message),
            Message(role="user", content=message.content),
        ]
