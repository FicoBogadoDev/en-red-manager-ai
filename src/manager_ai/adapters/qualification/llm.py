from __future__ import annotations

from pydantic import BaseModel, Field, ValidationError

from manager_ai.adapters.llm.text_generation.wiring import LLMTextGenerationPort
from manager_ai.adapters.qualification.catalog import (
    DEFAULT_SERVICE_CATALOG_PATH,
    ServiceCatalog,
    load_service_catalog,
)
from manager_ai.models.conversation import ContactThreadState, ConversationMessage, JobState, Message
from manager_ai.ports.qualification import (
    QualifiedServiceItem,
    QualificationDecision,
    QualificationPort,
    ServiceQualification,
)


class _QualificationOutput(BaseModel):
    decision: QualificationDecision
    reason: str
    reply: str | None = None
    side_reply: str | None = None
    service_items: list[QualifiedServiceItem] = Field(default_factory=list)
    unsupported_items: list[QualifiedServiceItem] = Field(default_factory=list)
    unknown_items: list[QualifiedServiceItem] = Field(default_factory=list)


def _recent_history(thread: ContactThreadState, latest_message: ConversationMessage) -> list[Message]:
    messages: list[Message] = []
    for item in thread.history[-8:]:
        if item.id == latest_message.id:
            continue
        messages.append(Message(role=item.role.value, content=item.content))
    return messages


class LLMQualificationAdapter:
    def __init__(
        self,
        llm: LLMTextGenerationPort,
        catalog: ServiceCatalog | None = None,
    ) -> None:
        self._llm = llm
        self._catalog = catalog or load_service_catalog(DEFAULT_SERVICE_CATALOG_PATH)

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
            side_reply=parsed.side_reply,
            service_items=parsed.service_items,
            unsupported_items=parsed.unsupported_items,
            unknown_items=parsed.unknown_items,
        )

    def _system_prompt(self, job: JobState) -> str:
        return (
            "Sos el clasificador de calificacion de servicio de En Red Rosario. "
            "Clasifica el ultimo mensaje del cliente como JSON estricto usando este catalogo:\n"
            f"{self._catalog.raw_markdown}\n\n"
            "Analiza a nivel de item, no solo a nivel de mensaje completo. "
            "Usa service_items para items ofrecidos por En Red, unsupported_items para items "
            "adyacentes o claramente fuera de rubro, y unknown_items para items ambiguos. "
            "Usa decision='service' si hay al menos un item ofrecido o si el trabajo actual ya "
            "venia siendo un trabajo ofrecido. "
            "Usa decision='not_service' solo si no hay items ofrecidos ni trabajo actual ofrecido "
            "y el mensaje menciona claramente items no ofrecidos. "
            "Usa decision='unclear' para saludos, chitchat, preguntas vagas, falta de informacion "
            "o solo items ambiguos. "
            "Nunca trates informacion faltante como motivo de descarte. "
            "Si el trabajo actual ya tiene tipo de instalacion o intencion de servicio, mantenelo como service "
            "aunque el ultimo mensaje sea casual o incluya un extra no ofrecido. "
            "Cuando haya items ofrecidos y no ofrecidos en el mismo mensaje, decision debe ser service. "
            "Devolve exactamente este JSON: "
            '{"decision":"service|not_service|unclear","reason":"...",'
            '"reply":null,"side_reply":null,'
            '"service_items":[{"raw_text":"...","normalized_service":"...",'
            '"scope_status":"in_scope","reply_label":"...","rejection_phrase":null}],'
            '"unsupported_items":[{"raw_text":"...","normalized_service":"...",'
            '"scope_status":"adjacent_unsupported","reply_label":"...",'
            '"rejection_phrase":"No hacemos ese trabajo."}],'
            '"unknown_items":[{"raw_text":"...","normalized_service":"...",'
            '"scope_status":"unknown","reply_label":"...","rejection_phrase":null}]}. '
            "reply puede ser una respuesta breve en espanol rioplatense cuando decision sea unclear o not_service. "
            "side_reply puede ser una frase breve para rechazar solo extras no ofrecidos cuando decision sea service.\n\n"
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
