import json
from pathlib import Path

from manager_ai.models.conversation import ConversationState


class JsonFileStorageAdapter:
    """Stores one JSON file per conversation under a configurable directory."""

    def __init__(self, directory: str) -> None:
        self._directory = Path(directory)
        self._directory.mkdir(parents=True, exist_ok=True)

    def _path_for(self, phone: str) -> Path:
        safe_name = phone.replace("+", "").replace(" ", "_")
        return self._directory / f"{safe_name}.json"

    def load(self, phone: str) -> ConversationState | None:
        file_path = self._path_for(phone)
        if not file_path.exists():
            return None
        data = json.loads(file_path.read_text(encoding="utf-8"))
        return ConversationState.model_validate(data)

    def save(self, phone: str, state: ConversationState) -> None:
        file_path = self._path_for(phone)
        file_path.write_text(
            state.model_dump_json(indent=2),
            encoding="utf-8",
        )
