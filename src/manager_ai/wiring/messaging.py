from manager_ai.adapters.messaging.log import LogMessagingAdapter
from manager_ai.ports.messaging import MessagingPort
from manager_ai.wiring.settings import MessagingConfig


def build_messaging(_cfg: MessagingConfig) -> MessagingPort:
    return LogMessagingAdapter()
