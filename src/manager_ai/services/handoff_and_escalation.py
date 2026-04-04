from __future__ import annotations

from manager_ai.models.conversation import (
    ContactThreadState,
    EscalationAction,
    EscalationReason,
    JobState,
    JobStatus,
)


def maybe_escalate(thread: ContactThreadState, job: JobState) -> list[EscalationAction]:
    actions: list[EscalationAction] = []
    if len([candidate for candidate in thread.jobs if candidate.status not in {JobStatus.CLOSED, JobStatus.DISQUALIFIED, JobStatus.ABANDONED}]) > 1:
        actions.append(
            EscalationAction(
                reason=EscalationReason.MULTIPLE_ACTIVE_JOBS,
                job_id=job.id,
                message="El hilo tiene más de un trabajo activo y requiere revisión humana.",
            )
        )
    if len(job.stakeholders) > 1:
        actions.append(
            EscalationAction(
                reason=EscalationReason.STAKEHOLDER_CONFLICT,
                job_id=job.id,
                message="Hay múltiples stakeholders en el trabajo; conviene revisión humana.",
            )
        )
    if job.status == JobStatus.NEGOTIATING:
        actions.append(
            EscalationAction(
                reason=EscalationReason.COMMERCIAL_OVERRIDE,
                job_id=job.id,
                message="El trabajo entró en negociación comercial y debe revisarlo una persona.",
            )
        )
    return actions
