from typing import Protocol

from manager_ai.models.conversation import ExternalActionRequest, JobState, ScheduleRequest


class SchedulingPort(Protocol):
    def request(self, job: JobState, schedule_request: ScheduleRequest) -> ExternalActionRequest: ...
