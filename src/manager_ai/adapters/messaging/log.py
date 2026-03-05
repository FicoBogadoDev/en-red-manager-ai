class LogMessagingAdapter:
    """Logs outgoing messages to stdout instead of sending via WhatsApp."""

    def send(self, to: str, text: str) -> None:
        print(f"\n[LogMessagingAdapter] → {to}: {text}")
