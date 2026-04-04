from typing import Protocol

from manager_ai.models.conversation import ContactThreadState, ConversationMessage, JobState


class StructuredExtractionPort(Protocol):
    def extract(
        self,
        thread: ContactThreadState,
        job: JobState,
        message: ConversationMessage,
    ) -> JobState: ...
