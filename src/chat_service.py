from sqlalchemy import select

from src.database import async_session_factory
from src.models import ChatMessage


class ChatService:

    # =====================================================
    # SAVE MESSAGE
    # =====================================================

    async def save_message(
        self,
        session_id,
        role,
        content,
        citations=None
    ):

        async with async_session_factory() as db:

            message = ChatMessage(
                session_id=session_id,
                role=role,
                content=content,
                citations=citations
            )

            db.add(message)

            await db.commit()

            await db.refresh(message)

            return message


    # =====================================================
    # RECENT MESSAGES
    # =====================================================

    async def get_recent_messages(
        self,
        session_id,
        limit=3
    ):

        statement = (
            select(ChatMessage)

            .where(
                ChatMessage.session_id
                == session_id
            )

            .order_by(
                ChatMessage.created_at.desc(),
                ChatMessage.id.desc()
            )

            .limit(limit)
        )


        async with async_session_factory() as db:

            result = await db.execute(
                statement
            )

            messages = list(
                result.scalars().all()
            )


        messages.reverse()

        return messages


    # =====================================================
    # ALL MESSAGES
    # =====================================================

    async def get_messages(
        self,
        session_id
    ):

        statement = (
            select(ChatMessage)

            .where(
                ChatMessage.session_id
                == session_id
            )

            .order_by(
                ChatMessage.created_at.asc(),
                ChatMessage.id.asc()
            )
        )


        async with async_session_factory() as db:

            result = await db.execute(
                statement
            )

            return list(
                result.scalars().all()
            )