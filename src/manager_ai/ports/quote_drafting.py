from typing import Protocol

from manager_ai.models.conversation import JobState, QuoteVersion


class QuoteDraftingPort(Protocol):
    def draft_quote(self, job: JobState, rough: bool) -> QuoteVersion: ...
