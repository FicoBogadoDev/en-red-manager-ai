from typing import Protocol

from manager_ai.models.conversation import ContactThreadState, IntentType, JobState


class ConversationReplyPort(Protocol):
    def draft_reply(
        self,
        thread: ContactThreadState,
        job: JobState,
        intent: IntentType,
        route: str,
        fallback_text: str,
    ) -> str: ...
