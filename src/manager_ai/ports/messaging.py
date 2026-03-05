from typing import Protocol


class MessagingPort(Protocol):
    def send(self, to: str, text: str) -> None: ...
