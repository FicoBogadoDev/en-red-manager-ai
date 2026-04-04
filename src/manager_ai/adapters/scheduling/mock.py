from __future__ import annotations

from manager_ai.models.conversation import ExternalActionRequest, JobState, ScheduleRequest
from manager_ai.ports.scheduling import SchedulingPort


class MockSchedulingAdapter(SchedulingPort):
    def request(self, job: JobState, schedule_request: ScheduleRequest) -> ExternalActionRequest:
        return ExternalActionRequest(
            kind="schedule",
            job_id=job.id,
            summary="schedule_request_created",
            payload={
                "window": schedule_request.requested_window,
                "reason": schedule_request.reason,
            },
        )
