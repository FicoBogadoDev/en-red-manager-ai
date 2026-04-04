from typing import Protocol

from manager_ai.models.conversation import ExternalActionRequest, JobState


class ReminderPort(Protocol):
    def create_follow_up(self, job: JobState, summary: str) -> ExternalActionRequest: ...
