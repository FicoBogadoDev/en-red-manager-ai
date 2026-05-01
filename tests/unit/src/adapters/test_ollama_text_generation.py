from typing import Mapping

import pytest

from manager_ai.adapters.llm.text_generation.ollama import OllamaAdapter
from manager_ai.models.conversation import Message


class FakeOllamaHTTPClient:
    def __init__(self, response: Mapping[str, object]) -> None:
        self.response = response
        self.calls: list[dict[str, object]] = []

    def post_json(
        self,
        url: str,
        payload: Mapping[str, object],
        timeout_seconds: float,
    ) -> Mapping[str, object]:
        self.calls.append(
            {
                "url": url,
                "payload": payload,
                "timeout_seconds": timeout_seconds,
            }
        )
        return self.response


def test_ollama_adapter_sends_expected_request_and_returns_text() -> None:
    client = FakeOllamaHTTPClient(
        response={"message": {"role": "assistant", "content": "Hola mundo"}}
    )
    adapter = OllamaAdapter(
        model="llama-test",
        client=client,
        base_url="http://localhost:11434/",
        timeout_seconds=12.5,
    )

    result = adapter.complete(
        system_prompt="Responde con claridad.",
        messages=[
            Message(role="system", content="ignored as history"),
            Message(role="user", content="Hola"),
            Message(role="assistant", content="Buenas"),
        ],
    )

    assert result == "Hola mundo"
    assert client.calls == [
        {
            "url": "http://localhost:11434/api/chat",
            "timeout_seconds": 12.5,
            "payload": {
                "model": "llama-test",
                "stream": False,
                "messages": [
                    {"role": "system", "content": "Responde con claridad."},
                    {"role": "user", "content": "Hola"},
                    {"role": "assistant", "content": "Buenas"},
                ],
            },
        }
    ]


def test_ollama_adapter_rejects_missing_text_content() -> None:
    adapter = OllamaAdapter(
        model="llama-test",
        client=FakeOllamaHTTPClient(response={"message": {"role": "assistant"}}),
    )

    with pytest.raises(RuntimeError, match="text content"):
        adapter.complete(system_prompt="System", messages=[])
