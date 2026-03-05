from manager_ai.agent.prompts import (
    COLLECTION_SYSTEM_PROMPT,
    HANDOFF_MESSAGE,
    NOT_QUALIFIED_MESSAGE,
    QUALIFICATION_SYSTEM_PROMPT,
)
from manager_ai.models.client import ClientChart
from manager_ai.models.conversation import ConversationStage, ConversationState
from manager_ai.ports.llm import LLMPort
from manager_ai.ports.messaging import MessagingPort
from manager_ai.ports.storage import StoragePort
from manager_ai.services import collection, handoff, qualification


class Agent:
    def __init__(
        self,
        llm: LLMPort,
        messaging: MessagingPort,
        storage: StoragePort,
    ) -> None:
        self._llm = llm
        self._messaging = messaging
        self._storage = storage

    def handle_message(self, phone: str, text: str) -> None:
        state = self._load_or_create(phone)

        if state.stage == ConversationStage.DONE:
            # Conversation is closed — ignore further messages
            return

        if state.stage == ConversationStage.QUALIFYING:
            state, reply = qualification.run_qualification(
                state=state,
                user_message=text,
                llm=self._llm,
                system_prompt=QUALIFICATION_SYSTEM_PROMPT,
            )
            if state.stage == ConversationStage.DONE:
                # Not qualified — override reply with the standard rejection message
                reply = NOT_QUALIFIED_MESSAGE
                self._messaging.send(to=phone, text=reply)
                self._storage.save(phone, state)
                return
            self._messaging.send(to=phone, text=reply)

        if state.stage == ConversationStage.COLLECTING:
            state, reply = collection.run_collection(
                state=state,
                user_message=text,
                llm=self._llm,
                system_prompt=COLLECTION_SYSTEM_PROMPT,
            )
            self._messaging.send(to=phone, text=reply)

        if state.stage == ConversationStage.HANDOFF_PENDING:
            state = handoff.run_handoff(
                state=state,
                closing_message=HANDOFF_MESSAGE,
                messaging=self._messaging,
            )

        self._storage.save(phone, state)

    def _load_or_create(self, phone: str) -> ConversationState:
        existing = self._storage.load(phone)
        if existing is not None:
            return existing
        return ConversationState(
            phone=phone,
            client=ClientChart(phone=phone),
        )
