from manager_ai.models.conversation import ConversationStage, ConversationState, Message
from manager_ai.ports.llm import LLMPort


def is_qualified(llm_response: str) -> bool:
    """Return True if the LLM marked the conversation as QUALIFIED."""
    return "QUALIFIED" in llm_response and "NOT_QUALIFIED" not in llm_response


def run_qualification(
    state: ConversationState,
    user_message: str,
    llm: LLMPort,
    system_prompt: str,
) -> tuple[ConversationState, str]:
    """
    Run one qualification turn.

    Returns the updated state and the assistant reply to send back to the client.
    """
    updated_history = state.history + [Message(role="user", content=user_message)]

    messages_for_llm = [Message(role="system", content=system_prompt)] + updated_history
    llm_response = llm.complete(messages_for_llm)

    qualified = is_qualified(llm_response)
    # Strip the trailing keyword before sending the reply to the client
    reply = llm_response.replace("QUALIFIED", "").replace("NOT_QUALIFIED", "").strip()

    updated_history = updated_history + [Message(role="assistant", content=reply)]

    new_stage = ConversationStage.COLLECTING if qualified else ConversationStage.DONE
    new_state = state.model_copy(
        update={"stage": new_stage, "history": updated_history}
    )
    return new_state, reply
