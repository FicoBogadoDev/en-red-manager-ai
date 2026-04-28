from manager_ai.models.conversation import Message


class LogLLMAdapter:
    """Prints messages to stdout instead of calling an LLM. Useful for dev without an API key."""

    def complete(self, system_prompt: str, messages: list[Message]) -> str:
        print("\n[LogLLMAdapter] Messages sent to LLM:")
        print(f"  [system]: {system_prompt[:120]}")
        for message in messages:
            print(f"  [{message.role}]: {message.content[:120]}")
        stub_response = "[Respuesta simulada del agente]"
        print(f"  [response]: {stub_response}")
        return stub_response
