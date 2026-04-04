from manager_ai.models.conversation import ContactThreadState, IntentType, JobState
from manager_ai.ports.conversation_reply import ConversationReplyPort


class RulesConversationReplyAdapter(ConversationReplyPort):
    def draft_reply(
        self,
        thread: ContactThreadState,
        job: JobState,
        intent: IntentType,
        route: str,
        fallback_text: str,
    ) -> str:
        return fallback_text
