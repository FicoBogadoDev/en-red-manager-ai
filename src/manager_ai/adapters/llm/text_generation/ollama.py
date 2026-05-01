from __future__ import annotations

import json
from typing import Any, Mapping, Protocol
from urllib import error, request

from manager_ai.models.conversation import Message


class OllamaHTTPClient(Protocol):
    def post_json(
        self,
        url: str,
        payload: Mapping[str, object],
        timeout_seconds: float,
    ) -> Mapping[str, object]: ...


class UrllibOllamaHTTPClient:
    def post_json(
        self,
        url: str,
        payload: Mapping[str, object],
        timeout_seconds: float,
    ) -> Mapping[str, object]:
        body = json.dumps(payload).encode("utf-8")
        http_request = request.Request(
            url=url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(http_request, timeout=timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
        except error.URLError as exc:
            raise RuntimeError(f"Ollama request failed: {exc}") from exc

        parsed = json.loads(response_body)
        if not isinstance(parsed, dict):
            raise RuntimeError("Ollama response was not a JSON object.")
        return parsed


class OllamaAdapter:
    def __init__(
        self,
        model: str,
        client: OllamaHTTPClient,
        base_url: str = "http://localhost:11434",
        timeout_seconds: float = 60.0,
    ) -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._client = client

    def complete(self, system_prompt: str, messages: list[Message]) -> str:
        response = self._client.post_json(
            url=f"{self._base_url}/api/chat",
            payload={
                "model": self._model,
                "stream": False,
                "messages": _to_ollama_messages(system_prompt, messages),
            },
            timeout_seconds=self._timeout_seconds,
        )
        return _response_text(response)


def _to_ollama_messages(
    system_prompt: str,
    messages: list[Message],
) -> list[dict[str, str]]:
    ollama_messages = [{"role": "system", "content": system_prompt}]
    for message in messages:
        if message.role in {"user", "assistant"}:
            ollama_messages.append({"role": message.role, "content": message.content})
    return ollama_messages


def _response_text(response: Mapping[str, Any]) -> str:
    message = response.get("message")
    if not isinstance(message, dict):
        raise RuntimeError("Ollama response did not include a message object.")

    content = message.get("content")
    if not isinstance(content, str):
        raise RuntimeError("Ollama response message did not include text content.")

    return content
