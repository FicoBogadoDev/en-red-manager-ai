from typing import Protocol

from manager_ai.models.conversation import Message
from manager_ai.models.extraction import ExtractedClientData


class ExtractorPort(Protocol):
    def collect(self, messages: list[Message]) -> tuple[str, ExtractedClientData]:
        """
        Run a full collection turn: send messages to the LLM and return both the
        conversational reply and structured extracted data.

        Args:
            messages: Full message list (system + history + user).

        Returns:
            A tuple of (reply_text, ExtractedClientData). On failure returns
            ("", ExtractedClientData()) — never raises.
        """
        ...
