from manager_ai.models.conversation import ContactThreadState, ConversationEvent


class InMemoryStorageAdapter:
    """Stores contact threads in a dict. For unit tests only."""

    def __init__(self) -> None:
        self._store: dict[str, ContactThreadState] = {}

    def load_thread(self, phone: str) -> ContactThreadState | None:
        return self._store.get(phone)

    def save_thread(self, thread: ContactThreadState) -> None:
        self._store[thread.phone] = thread

    def append_event(self, phone: str, event: ConversationEvent) -> None:
        thread = self._store.get(phone)
        if thread is None:
            return
        thread.events.append(event)

    def list_thread_phones(self) -> list[str]:
        return list(self._store.keys())

    def load(self, phone: str) -> ContactThreadState | None:
        return self.load_thread(phone)

    def save(self, phone: str, state: ContactThreadState) -> None:
        self.save_thread(state)
