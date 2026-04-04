from __future__ import annotations

from manager_ai.models.conversation import (
    Appointment,
    AppointmentStatus,
    ExternalActionRequest,
    IntentType,
    JobState,
    JobStatus,
    ScheduleRequest,
)
from manager_ai.ports.scheduling import SchedulingPort


def handle_scheduling(
    job: JobState,
    intent: IntentType,
    scheduler: SchedulingPort,
) -> tuple[JobState, ExternalActionRequest | None, str | None]:
    updated = job.model_copy(deep=True)
    if intent not in {IntentType.SCHEDULING, IntentType.RESCHEDULING}:
        return updated, None, None

    request = ScheduleRequest(
        requested_window="cliente_pidio_coordinar",
        reason="reschedule" if intent == IntentType.RESCHEDULING else "schedule",
    )
    updated.schedule_requests.append(request)
    updated.status = JobStatus.RESCHEDULE_NEEDED if intent == IntentType.RESCHEDULING else JobStatus.SCHEDULED
    appointment_status = (
        AppointmentStatus.RESCHEDULE_REQUESTED if intent == IntentType.RESCHEDULING else AppointmentStatus.REQUESTED
    )
    updated.appointments.append(
        Appointment(status=appointment_status, notes=request.reason)
    )
    external_action = scheduler.request(updated, request)
    response = (
        "Anoto el pedido de reprogramación y se lo paso al equipo para coordinar."
        if intent == IntentType.RESCHEDULING
        else "Perfecto, dejo pedido de coordinación para que el equipo confirme disponibilidad."
    )
    return updated, external_action, response
