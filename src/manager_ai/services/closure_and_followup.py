from __future__ import annotations

from manager_ai.models.conversation import IntentType, JobState, JobStatus
from manager_ai.ports.reminder import ReminderPort


def apply_closure_updates(
    job: JobState,
    intent: IntentType,
    reminders: ReminderPort,
) -> tuple[JobState, str | None, object | None]:
    updated = job.model_copy(deep=True)
    if intent == IntentType.PAYMENT:
        updated.status = JobStatus.PAYMENT_PENDING
        return (
            updated,
            "Perfecto, dejo asentado el tema de pago para seguimiento del equipo.",
            reminders.create_follow_up(updated, "payment_follow_up"),
        )
    if intent == IntentType.POST_INSTALL:
        updated.status = JobStatus.COMPLETED
        updated.closure_reason = "client_confirmed_installation"
        return updated, "Gracias por la confirmación. Dejo cerrado el trabajo y cualquier ajuste lo retomamos por acá.", None
    return updated, None, None
