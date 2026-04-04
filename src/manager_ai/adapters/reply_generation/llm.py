from __future__ import annotations

from manager_ai.models.conversation import ContactThreadState, IntentType, JobState, Message
from manager_ai.ports.conversation_reply import ConversationReplyPort
from manager_ai.ports.llm import LLMPort


def _conversation_messages(thread: ContactThreadState) -> list[Message]:
    recent_history = thread.history[-8:]
    return [
        Message(role=message.role.value, content=message.content)
        for message in recent_history
    ]


class LLMConversationReplyAdapter(ConversationReplyPort):
    def __init__(self, llm: LLMPort) -> None:
        self._llm = llm

    def draft_reply(
        self,
        thread: ContactThreadState,
        job: JobState,
        intent: IntentType,
        route: str,
        fallback_text: str,
    ) -> str:
        messages = [
            Message(
                role="system",
                content=(
                    "Sos el asistente virtual de En Red Rosario. "
                    "Respondé en español rioplatense, con tono humano, breve y claro para WhatsApp. "
                    "No inventes datos. Si faltan datos, pedí solo el próximo dato más importante. "
                    "No menciones procesos internos, rutas, estados ni IDs. "
                    "Tu objetivo comercial es avanzar la conversación sin abrumar."
                ),
            ),
            Message(
                role="system",
                content=(
                    f"Intent detectado: {intent.value}\n"
                    f"Ruta seleccionada: {route}\n"
                    f"Trabajo actual: {job.title}\n"
                    f"Estado del trabajo: {job.status.value}\n"
                    f"Datos conocidos: nombre={job.contact_name}, direccion={job.scope.address}, ciudad={job.scope.city}, "
                    f"tipo={job.scope.installation_type}, areas={self._net_area_summary(job)}\n"
                    f"Campos faltantes: {', '.join(job.missing_fields) if job.missing_fields else 'ninguno'}\n"
                    f"Respuesta base sugerida: {fallback_text}"
                ),
            ),
            *_conversation_messages(thread),
            Message(
                role="user",
                content=(
                    "Redactá la próxima respuesta al cliente. "
                    "Mantenela en 1 o 2 frases cortas. "
                    "Si la respuesta base ya es correcta, podés reformularla suavemente sin cambiar el objetivo."
                ),
            ),
        ]
        reply = self._llm.complete(messages).strip()
        return reply or fallback_text

    def _net_area_summary(self, job: JobState) -> str:
        if not job.scope.net_areas:
            return "ninguna"
        return ", ".join(
            f"{area.label or f'Area {index}'}={area.width_meters}x{area.height_meters}"
            for index, area in enumerate(job.scope.net_areas, start=1)
        )
