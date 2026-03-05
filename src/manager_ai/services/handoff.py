from manager_ai.models.conversation import ConversationStage, ConversationState
from manager_ai.ports.messaging import MessagingPort


def run_handoff(
    state: ConversationState,
    closing_message: str,
    messaging: MessagingPort,
) -> ConversationState:
    """
    Send the closing message to the client and mark the conversation as DONE.
    In a future iteration this could also notify the human team.
    """
    messaging.send(to=state.phone, text=closing_message)
    return state.model_copy(
        update={
            "stage": ConversationStage.DONE,
            "handoff_reason": "all_fields_collected",
        }
    )
