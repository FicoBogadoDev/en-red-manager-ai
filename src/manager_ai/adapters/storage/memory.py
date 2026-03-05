from manager_ai.models.conversation import ConversationState


class InMemoryStorageAdapter:
    """Stores conversation state in a dict. For unit tests only."""

    def __init__(self) -> None:
        self._store: dict[str, ConversationState] = {}

    def load(self, phone: str) -> ConversationState | None:
        return self._store.get(phone)

    def save(self, phone: str, state: ConversationState) -> None:
        self._store[phone] = state
