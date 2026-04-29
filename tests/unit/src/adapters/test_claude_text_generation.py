from anthropic.types import Message as ClaudeMessage
from anthropic.types import MessageParam, TextBlock, ThinkingBlock, Usage

from manager_ai.adapters.llm.text_generation.claude import (
    ClaudeAdapter,
    ClaudeMessagesClient,
)
from manager_ai.models.conversation import Message


class FakeMessagesClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create(
        self,
        *,
        model: str,
        max_tokens: int,
        system: str,
        messages: list[MessageParam],
    ) -> ClaudeMessage:
        self.calls.append(
            {
                "model": model,
                "max_tokens": max_tokens,
                "system": system,
                "messages": messages,
            }
        )
        return ClaudeMessage(
            id="msg_test",
            content=[
                TextBlock(text="Hola", type="text"),
                ThinkingBlock(signature="signature", thinking="hidden", type="thinking"),
                TextBlock(text=" mundo", type="text"),
            ],
            model=model,
            role="assistant",
            stop_reason="end_turn",
            stop_sequence=None,
            type="message",
            usage=Usage(input_tokens=1, output_tokens=2),
        )


class FakeClaudeClient:
    def __init__(self, messages: ClaudeMessagesClient) -> None:
        self.messages = messages


def test_claude_adapter_sends_expected_request_and_returns_text() -> None:
    messages_client = FakeMessagesClient()
    client = FakeClaudeClient(messages=messages_client)
    adapter = ClaudeAdapter(model="claude-test", client=client)

    result = adapter.complete(
        system_prompt="Respondé con claridad.",
        messages=[
            Message(role="system", content="ignored as history"),
            Message(role="user", content="Hola"),
            Message(role="assistant", content="Buenas"),
        ],
    )

    assert result == "Hola mundo"
    assert messages_client.calls == [
        {
            "model": "claude-test",
            "max_tokens": 1024,
            "system": "Respondé con claridad.",
            "messages": [
                {"role": "user", "content": "Hola"},
                {"role": "assistant", "content": "Buenas"},
            ],
        }
    ]
