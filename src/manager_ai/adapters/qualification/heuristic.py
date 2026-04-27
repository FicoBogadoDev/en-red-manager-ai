from __future__ import annotations

import unicodedata

from manager_ai.models.conversation import ContactThreadState, ConversationMessage, JobState
from manager_ai.ports.qualification import (
    QualificationDecision,
    QualificationPort,
    ServiceQualification,
)

_EXPLICIT_NON_SERVICE_TOKENS = (
    "pesca",
    "volley",
    "futbol",
    "red lan",
)

_SERVICE_TOKENS = (
    "red",
    "balcon",
    "techo",
    "terraza",
    "escalera",
    "proteccion",
    "seguridad",
    "gato",
    "mascota",
    "chico",
)


def _normalized_text(text: str) -> str:
    without_accents = unicodedata.normalize("NFKD", text)
    ascii_text = without_accents.encode("ascii", "ignore").decode("ascii")
    return ascii_text.lower()


class HeuristicQualificationAdapter(QualificationPort):
    def qualify(
        self,
        thread: ContactThreadState,
        job: JobState,
        message: ConversationMessage,
    ) -> ServiceQualification:
        if job.scope.service_intent or job.scope.installation_type:
            return ServiceQualification(
                decision=QualificationDecision.SERVICE,
                reason="Existing job already has service-fit evidence.",
            )

        text = _normalized_text(message.content)
        if any(token in text for token in _EXPLICIT_NON_SERVICE_TOKENS):
            return ServiceQualification(
                decision=QualificationDecision.NOT_SERVICE,
                reason="Message explicitly mentions an unsupported service.",
            )

        if any(token in text for token in _SERVICE_TOKENS):
            return ServiceQualification(
                decision=QualificationDecision.SERVICE,
                reason="Message includes En Red service keywords.",
            )

        return ServiceQualification(
            decision=QualificationDecision.UNCLEAR,
            reason="Message does not contain enough service-fit evidence.",
        )
