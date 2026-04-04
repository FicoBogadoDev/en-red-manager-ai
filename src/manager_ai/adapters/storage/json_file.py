import json
from pathlib import Path

from pydantic import ValidationError

from manager_ai.models.conversation import ContactThreadState, ConversationEvent


class JsonFileStorageAdapter:
    """Stores one JSON file per thread under a configurable directory."""

    def __init__(self, directory: str) -> None:
        self._directory = Path(directory)
        self._directory.mkdir(parents=True, exist_ok=True)

    def _path_for(self, phone: str) -> Path:
        safe_name = phone.replace("+", "").replace(" ", "_")
        return self._directory / f"{safe_name}.json"

    def load_thread(self, phone: str) -> ContactThreadState | None:
        file_path = self._path_for(phone)
        if not file_path.exists():
            return None
        data = json.loads(file_path.read_text(encoding="utf-8"))
        try:
            return ContactThreadState.model_validate(data)
        except ValidationError:
            return None

    def save_thread(self, thread: ContactThreadState) -> None:
        file_path = self._path_for(thread.phone)
        file_path.write_text(
            thread.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def append_event(self, phone: str, event: ConversationEvent) -> None:
        thread = self.load_thread(phone)
        if thread is None:
            return
        thread.events.append(event)
        self.save_thread(thread)

    def list_thread_phones(self) -> list[str]:
        phones: list[str] = []
        for path in self._directory.glob("*.json"):
            phone = "+" + path.stem
            if self.load_thread(phone) is not None:
                phones.append(phone)
        return phones

    def load(self, phone: str) -> ContactThreadState | None:
        return self.load_thread(phone)

    def save(self, phone: str, state: ContactThreadState) -> None:
        self.save_thread(state)

    def list_phones(self) -> list[str]:
        return self.list_thread_phones()
