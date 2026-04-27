from __future__ import annotations

from enum import Enum
from typing import Protocol

from pydantic import BaseModel

from manager_ai.models.conversation import ContactThreadState, ConversationMessage, JobState


class QualificationDecision(str, Enum):
    SERVICE = "service"
    NOT_SERVICE = "not_service"
    UNCLEAR = "unclear"


class ServiceQualification(BaseModel):
    decision: QualificationDecision
    reason: str | None = None
    reply: str | None = None


class QualificationPort(Protocol):
    def qualify(
        self,
        thread: ContactThreadState,
        job: JobState,
        message: ConversationMessage,
    ) -> ServiceQualification: ...
