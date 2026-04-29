from manager_ai.models.conversation import ConversationStage, ConversationState, Message
from manager_ai.adapters.llm.text_generation.wiring import LLMTextGenerationPort


def is_qualified(llm_response: str) -> bool:
    """Return True if the LLM marked the conversation as QUALIFIED."""
    return "QUALIFIED" in llm_response and "NOT_QUALIFIED" not in llm_response


def run_qualification(
    state: ConversationState,
    user_message: str,
    llm: LLMTextGenerationPort,
    system_prompt: str,
) -> tuple[ConversationState, str]:
    """
    Run one qualification turn.

    Returns the updated state and the assistant reply to send back to the client.
    """
    updated_history = state.history + [Message(role="user", content=user_message)]

    llm_response = llm.complete(system_prompt, updated_history)

    qualified = is_qualified(llm_response)
    # Strip the trailing keyword before sending the reply to the client
    reply = llm_response.replace("QUALIFIED", "").replace("NOT_QUALIFIED", "").strip()

    new_stage = ConversationStage.COLLECTING if qualified else ConversationStage.DONE

    if qualified:
        # Discard the qualification exchange from history — the agent will
        # fall through to collection, which will own this message turn.
        new_state = state.model_copy(update={"stage": new_stage})
    else:
        updated_history = updated_history + [Message(role="assistant", content=reply)]
        new_state = state.model_copy(update={"stage": new_stage, "history": updated_history})

    return new_state, reply
