from manager_ai.adapters.storage.json_file import JsonFileStorageAdapter
from manager_ai.adapters.storage.memory import InMemoryStorageAdapter
from manager_ai.ports.conversation_repository import ConversationRepositoryPort
from manager_ai.wiring.settings import JsonStorageConfig, StorageConfig


def build_storage(cfg: StorageConfig) -> ConversationRepositoryPort:
    if isinstance(cfg, JsonStorageConfig):
        return JsonFileStorageAdapter(directory=cfg.path)
    return InMemoryStorageAdapter()
