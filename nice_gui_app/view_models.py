from __future__ import annotations

from dataclasses import dataclass

from manager_ai.models.conversation import (
    ContactThreadState,
    ConversationEvent,
    JobState,
    JobStatus,
)

_OPEN_JOB_STATUSES = {
    JobStatus.NEW,
    JobStatus.QUALIFYING,
    JobStatus.AWAITING_EVIDENCE,
    JobStatus.SCOPING,
    JobStatus.ESTIMATE_READY,
    JobStatus.QUOTE_SENT,
    JobStatus.NEGOTIATING,
    JobStatus.APPROVED,
    JobStatus.READY_TO_SCHEDULE,
    JobStatus.SCHEDULED,
    JobStatus.RESCHEDULE_NEEDED,
    JobStatus.PAYMENT_PENDING,
}

_TRACE_GROUPS: dict[str, set[str]] = {
    "all": set(),
    "intent": {"intent_detected", "route_selected"},
    "extraction": {"extracted_data_updated", "missing_fields_updated"},
    "quote": {"quote_generated", "quote_superseded"},
    "scheduling": {"scheduling_requested", "external_action_created"},
    "escalation": {"escalation_triggered"},
    "closure": {"closure_transition", "service_disqualified"},
}


@dataclass(frozen=True)
class ThreadSummary:
    phone: str
    status: str
    active_job_count: int
    escalation_count: int
    last_activity: str


def active_job(thread: ContactThreadState, selected_job_id: str | None = None) -> JobState | None:
    if selected_job_id is not None:
        selected = thread.get_job(selected_job_id)
        if selected is not None:
            return selected
    return thread.get_job(thread.active_job_id)


def open_job_count(thread: ContactThreadState) -> int:
    return sum(1 for job in thread.jobs if job.status in _OPEN_JOB_STATUSES)


def make_thread_summary(thread: ContactThreadState) -> ThreadSummary:
    return ThreadSummary(
        phone=thread.phone,
        status=thread.status.value,
        active_job_count=open_job_count(thread),
        escalation_count=len(thread.escalation_flags),
        last_activity=thread.updated_at.isoformat(timespec="seconds"),
    )


def job_options(thread: ContactThreadState) -> dict[str, str]:
    return {
        job.id: f"{job.title} [{job.status.value}]"
        for job in thread.jobs
    }


def latest_quote(job: JobState) -> object | None:
    return job.quotes[-1] if job.quotes else None


def latest_appointment(job: JobState) -> object | None:
    return job.appointments[-1] if job.appointments else None


def filtered_events(
    thread: ContactThreadState,
    selected_job_id: str | None,
    include_thread_wide: bool,
    trace_group: str,
) -> list[ConversationEvent]:
    allowed_kinds = _TRACE_GROUPS.get(trace_group, set())
    events: list[ConversationEvent] = []
    for event in thread.events:
        if selected_job_id is not None and event.job_id not in {selected_job_id, None if include_thread_wide else "__never__"}:
            continue
        if event.job_id is None and not include_thread_wide:
            continue
        if allowed_kinds and event.kind not in allowed_kinds:
            continue
        events.append(event)
    return sorted(events, key=lambda event: event.occurred_at)
