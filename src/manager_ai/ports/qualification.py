from __future__ import annotations

from enum import Enum
from typing import Protocol

from pydantic import BaseModel, Field

from manager_ai.models.conversation import ContactThreadState, ConversationMessage, JobState


class QualificationDecision(str, Enum):
    SERVICE = "service"
    NOT_SERVICE = "not_service"
    UNCLEAR = "unclear"


class QualificationScopeStatus(str, Enum):
    IN_SCOPE = "in_scope"
    ADJACENT_UNSUPPORTED = "adjacent_unsupported"
    UNKNOWN = "unknown"
    META = "meta"


class QualifiedServiceItem(BaseModel):
    raw_text: str
    normalized_service: str
    scope_status: QualificationScopeStatus
    reply_label: str | None = None
    rejection_phrase: str | None = None


class ServiceQualification(BaseModel):
    decision: QualificationDecision
    reason: str | None = None
    reply: str | None = None
    side_reply: str | None = None
    service_items: list[QualifiedServiceItem] = Field(default_factory=list)
    unsupported_items: list[QualifiedServiceItem] = Field(default_factory=list)
    unknown_items: list[QualifiedServiceItem] = Field(default_factory=list)


class QualificationPort(Protocol):
    def qualify(
        self,
        thread: ContactThreadState,
        job: JobState,
        message: ConversationMessage,
    ) -> ServiceQualification: ...
