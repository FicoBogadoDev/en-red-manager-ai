from typing import Protocol

from manager_ai.models.conversation import ContactThreadState, ConversationMessage, IntentType, JobState


class MessageClassifierPort(Protocol):
    def classify(
        self,
        thread: ContactThreadState,
        job: JobState | None,
        message: ConversationMessage,
    ) -> IntentType: ...
