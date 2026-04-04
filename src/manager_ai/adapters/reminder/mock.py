from __future__ import annotations

from manager_ai.models.conversation import ExternalActionRequest, JobState
from manager_ai.ports.reminder import ReminderPort


class MockReminderAdapter(ReminderPort):
    def create_follow_up(self, job: JobState, summary: str) -> ExternalActionRequest:
        return ExternalActionRequest(
            kind="reminder",
            job_id=job.id,
            summary=summary,
            payload={"job_status": job.status.value},
        )
