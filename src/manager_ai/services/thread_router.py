from __future__ import annotations

from datetime import timedelta

from manager_ai.models.conversation import ContactThreadState, IntentType, JobState, JobStatus, utc_now

_TERMINAL_JOB_STATUSES = {
    JobStatus.CLOSED,
    JobStatus.DISQUALIFIED,
    JobStatus.ABANDONED,
}


def should_open_new_job(thread: ContactThreadState, intent: IntentType) -> bool:
    active_job = thread.get_job(thread.active_job_id)
    if active_job is None:
        return True
    if intent == IntentType.NEW_INQUIRY and active_job.status in _TERMINAL_JOB_STATUSES:
        return True
    if intent == IntentType.NEW_INQUIRY and len(_active_jobs(thread)) >= 1:
        return True
    if active_job.updated_at <= utc_now() - timedelta(days=45):
        return True
    return False


def select_job(thread: ContactThreadState, intent: IntentType) -> JobState | None:
    if should_open_new_job(thread, intent):
        return None
    return thread.get_job(thread.active_job_id)


def add_job(thread: ContactThreadState, title: str = "Nueva consulta") -> JobState:
    job = JobState(title=title, status=JobStatus.QUALIFYING)
    thread.jobs.append(job)
    thread.active_job_id = job.id
    thread.updated_at = utc_now()
    return job


def _active_jobs(thread: ContactThreadState) -> list[JobState]:
    return [
        job
        for job in thread.jobs
        if job.status not in _TERMINAL_JOB_STATUSES
    ]
