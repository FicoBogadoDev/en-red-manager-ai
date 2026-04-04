from manager_ai.models.conversation import ConversationMessage, IncomingMessage, MessageRole


def ingest_message(message: IncomingMessage) -> ConversationMessage:
    return ConversationMessage(
        role=MessageRole.USER,
        content=message.text.strip(),
        created_at=message.received_at,
        attachments=message.attachments,
        source=message.source,
    )
