import os

import anthropic
import instructor
from pydantic import BaseModel, Field

from manager_ai.models.conversation import Message
from manager_ai.models.extraction import ExtractedClientData


class _CollectionTurn(BaseModel):
    reply: str = Field(description="Respuesta conversacional en español rioplatense.")
    data: ExtractedClientData


class InstructorExtractor:
    """
    Structured extractor using Instructor + Anthropic.

    Makes a single Anthropic API call that returns both the conversational reply
    and the structured ExtractedClientData. The system prompt from the messages
    list is used directly so no secondary extraction prompt is needed.
    """

    def __init__(self, model: str, api_key_env: str) -> None:
        api_key = os.environ.get(api_key_env)
        # Keep the raw client; wrap with instructor lazily on first collect() call
        # so that any mlflow.anthropic.autolog() patch is already active by then.
        self._raw_client = anthropic.Anthropic(api_key=api_key)
        self._client: instructor.Instructor | None = None
        self._model = model

    def collect(self, messages: list[Message]) -> tuple[str, ExtractedClientData]:
        """
        Run a full collection turn via Instructor.

        Returns the conversational reply and structured data in one API call.
        On any failure returns ("", ExtractedClientData()) — never raises.
        """
        system_text = next(
            (m.content for m in messages if m.role == "system"), ""
        )
        convo = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role != "system"
        ]
        if self._client is None:
            self._client = instructor.from_anthropic(self._raw_client)
        try:
            result: _CollectionTurn = self._client.messages.create(
                model=self._model,
                max_tokens=1024,
                system=system_text,
                messages=convo,
                response_model=_CollectionTurn,
            )
            return result.reply, result.data
        except Exception:
            return "", ExtractedClientData()
