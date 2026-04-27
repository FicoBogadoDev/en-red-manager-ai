from __future__ import annotations

import unicodedata

from manager_ai.models.conversation import ContactThreadState, ConversationMessage, IntentType, JobState
from manager_ai.ports.message_classifier import MessageClassifierPort

_GREETING_ONLY = {"hola", "buenas", "buenos dias", "buen dia", "buenas tardes", "buenas noches"}


def _normalized_text(text: str) -> str:
    without_accents = unicodedata.normalize("NFKD", text)
    ascii_text = without_accents.encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_text.lower().strip(" .,!?").split())


def _contains_any(text: str, fragments: tuple[str, ...]) -> bool:
    return any(fragment in text for fragment in fragments)


class HeuristicMessageClassifier(MessageClassifierPort):
    def classify(
        self,
        thread: ContactThreadState,
        job: JobState | None,
        message: ConversationMessage,
    ) -> IntentType:
        text = message.content.lower()
        normalized_text = _normalized_text(message.content)

        if message.attachments and not text.strip():
            return IntentType.PROVIDE_EVIDENCE
        if normalized_text in _GREETING_ONLY:
            return IntentType.CHIT_CHAT
        if _contains_any(text, ("te sirve", "se puede mejorar", "descuento", "menos", "negoci", "podemos cerrar")):
            return IntentType.NEGOTIATION
        if _contains_any(text, ("reprogram", "reagend", "pasarlo", "otro dia", "otro día", "llueve")):
            return IntentType.RESCHEDULING
        if _contains_any(text, ("agendar", "coordinar", "cuando pueden", "cuándo pueden", "visita", "instalar", "martes", "miércoles", "miercoles", "jueves", "viernes", "sábado", "sabado")):
            return IntentType.SCHEDULING
        if _contains_any(text, ("presupuesto", "precio", "cuánto", "cuanto", "$", "sale", "costo")):
            return IntentType.QUOTE_QUESTION
        if _contains_any(text, ("transfer", "pago", "seña", "sena", "factura")):
            return IntentType.PAYMENT
        if _contains_any(text, ("gracias", "quedó", "quedo", "terminado", "instalado")):
            return IntentType.POST_INSTALL
        if _contains_any(text, ("foto", "medida", "mide", "adjunto", "te mando", "te paso")) or message.attachments:
            return IntentType.PROVIDE_EVIDENCE
        if _contains_any(text, ("otro balcon", "otro balcón", "además", "ademas", "también", "tambien", "otra direccion", "otra dirección", "otro depto")):
            return IntentType.NEW_INQUIRY
        if _contains_any(text, ("hola", "buenas", "consulta", "necesito", "quiero", "red", "balcon", "balcón", "terraza", "techo", "escalera")):
            return IntentType.NEW_INQUIRY
        if len(text.strip()) <= 6:
            return IntentType.CHIT_CHAT
        return IntentType.UNKNOWN
