from __future__ import annotations

from manager_ai.models.conversation import IntentType, JobState, JobStatus, QuoteStatus
from manager_ai.ports.quote_drafting import QuoteDraftingPort


def can_prepare_rough_quote(job: JobState) -> bool:
    return (
        job.scope.installation_type is not None
        and job.scope.has_complete_net_area()
    )


def ensure_quote(job: JobState, intent: IntentType, drafter: QuoteDraftingPort) -> tuple[JobState, str | None]:
    updated = job.model_copy(deep=True)
    if intent not in {IntentType.QUOTE_QUESTION, IntentType.NEGOTIATION}:
        return updated, None

    if not can_prepare_rough_quote(updated):
        updated.status = JobStatus.AWAITING_EVIDENCE
        return updated, "Puedo ir preparándolo, pero para cotizar bien necesito tipo de instalación y medidas aproximadas."

    rough = intent == IntentType.QUOTE_QUESTION and not updated.quotes
    quote = drafter.draft_quote(updated, rough=rough)
    if updated.quotes:
        updated.quotes[-1].status = QuoteStatus.SUPERSEDED
    updated.quotes.append(quote)
    updated.status = JobStatus.NEGOTIATING if intent == IntentType.NEGOTIATION else JobStatus.QUOTE_SENT
    prefix = "Estimación" if quote.kind.value == "rough" else "Cotización"
    response = f"{prefix} de referencia: ${quote.amount_ars:,} ARS. Queda sujeta a revisión humana.".replace(",", ".")
    return updated, response
