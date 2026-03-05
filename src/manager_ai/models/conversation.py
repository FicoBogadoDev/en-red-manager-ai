from enum import Enum

from pydantic import BaseModel

from manager_ai.models.client import ClientChart


class ConversationStage(str, Enum):
    QUALIFYING = "qualifying"
    COLLECTING = "collecting"
    HANDOFF_PENDING = "handoff_pending"
    DONE = "done"


class Message(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ConversationState(BaseModel):
    phone: str
    stage: ConversationStage = ConversationStage.QUALIFYING
    client: ClientChart
    history: list[Message] = []
    handoff_reason: str | None = None
