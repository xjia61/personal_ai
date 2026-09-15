from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.models import Conversation, Message


def make_title(message: str, max_length: int = 60) -> str:
    one_line = " ".join(message.split())
    if len(one_line) <= max_length:
        return one_line
    return one_line[: max_length - 1].rstrip() + "…"


async def get_recent_context(db: AsyncSession, conversation_id: int) -> list[dict[str, str]]:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.id.desc())
        .limit(settings.context_message_limit)
    )
    recent = list(result.scalars().all())
    recent.reverse()
    return [
        {"role": message.role, "content": message.content}
        for message in recent
        if message.role in {"user", "assistant"}
    ]


async def get_conversation(db: AsyncSession, conversation_id: int) -> Conversation | None:
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    return result.scalar_one_or_none()
