from typing import Protocol

from manager_ai.models.conversation import ConversationState


class StoragePort(Protocol):
    def load(self, phone: str) -> ConversationState | None: ...
    def save(self, phone: str, state: ConversationState) -> None: ...
