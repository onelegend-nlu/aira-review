from sqlalchemy import delete, select

from src.database import async_session_factory
from src.models import (
    ChatMessage,
    ChatSession,
    ChatSessionDocument,
    Document,
)


DEFAULT_SESSION_TITLE = "Cuộc trò chuyện mới"


def build_auto_title(
    text: str,
    max_length: int = 52,
) -> str:
    clean_text = " ".join(
        text.strip().split()
    )

    if not clean_text:
        return DEFAULT_SESSION_TITLE

    if len(clean_text) <= max_length:
        return clean_text

    return (
        clean_text[
            : max_length - 3
        ].rstrip()
        + "..."
    )


class SessionService:

    # =====================================================
    # CREATE SESSION
    # =====================================================

    async def create_session(
        self,
        title=None,
    ):
        async with async_session_factory() as db:

            chat_session = ChatSession(
                title=(
                    title
                    or DEFAULT_SESSION_TITLE
                )
            )

            db.add(chat_session)

            await db.commit()
            await db.refresh(chat_session)

            return chat_session


    # =====================================================
    # LIST SESSIONS
    # =====================================================

    async def list_sessions(self):
        async with async_session_factory() as db:

            statement = (
                select(ChatSession)
                .order_by(
                    ChatSession
                    .created_at
                    .desc()
                )
            )

            result = await db.execute(
                statement
            )

            return list(
                result
                .scalars()
                .all()
            )


    # =====================================================
    # GET SESSION
    # =====================================================

    async def get_session_by_id(
        self,
        session_id,
    ):
        async with async_session_factory() as db:

            return await db.get(
                ChatSession,
                session_id,
            )


    # =====================================================
    # GET LATEST SESSION
    # =====================================================

    async def get_latest_session(
        self,
    ):
        async with async_session_factory() as db:

            statement = (
                select(ChatSession)

                .order_by(
                    ChatSession
                    .created_at
                    .desc()
                )

                .limit(1)
            )

            result = await db.execute(
                statement
            )

            return (
                result
                .scalar_one_or_none()
            )


    # =====================================================
    # AUTO TITLE
    # =====================================================

    async def auto_title_if_default(
        self,
        session_id,
        first_message: str,
    ):
        async with async_session_factory() as db:

            chat_session = await db.get(
                ChatSession,
                session_id,
            )

            if chat_session is None:
                return None

            current_title = (
                chat_session.title
                or ""
            ).strip()

            if current_title not in {
                "",
                DEFAULT_SESSION_TITLE,
            }:
                return chat_session

            chat_session.title = (
                build_auto_title(
                    first_message
                )
            )

            await db.commit()
            await db.refresh(
                chat_session
            )

            return chat_session


    # =====================================================
    # DELETE SESSION
    # =====================================================

    async def delete_session(
        self,
        session_id,
    ) -> bool:

        async with async_session_factory() as db:

            chat_session = await db.get(
                ChatSession,
                session_id,
            )

            if chat_session is None:
                return False

            # Xóa chat history.
            await db.execute(
                delete(ChatMessage)
                .where(
                    ChatMessage.session_id
                    == session_id
                )
            )

            # Xóa liên kết session-document.
            #
            # Document/chunk không xóa tại đây
            # vì một document có thể được dùng
            # bởi session khác.
            await db.execute(
                delete(
                    ChatSessionDocument
                )
                .where(
                    ChatSessionDocument.session_id
                    == session_id
                )
            )

            await db.delete(
                chat_session
            )

            await db.commit()

            return True


    # =====================================================
    # ATTACH EXISTING DOCUMENT BY NAME
    # =====================================================

    async def attach_document_by_name(
        self,
        session_id,
        document_name,
    ):
        async with async_session_factory() as db:

            chat_session = await db.get(
                ChatSession,
                session_id,
            )

            if chat_session is None:
                raise ValueError(
                    "Không tìm thấy chat session."
                )

            statement = (
                select(Document)

                .where(
                    Document.name
                    == document_name
                )

                .where(
                    Document.status
                    == "ready"
                )

                .order_by(
                    Document
                    .created_at
                    .desc()
                )

                .limit(1)
            )

            result = await db.execute(
                statement
            )

            document = (
                result
                .scalar_one_or_none()
            )

            if document is None:
                raise ValueError(
                    f"Không tìm thấy document "
                    f"'{document_name}' "
                    f"ở trạng thái ready."
                )

            existing_statement = (
                select(
                    ChatSessionDocument
                )

                .where(
                    ChatSessionDocument.session_id
                    == session_id
                )

                .where(
                    ChatSessionDocument.document_id
                    == document.id
                )
            )

            existing_result = (
                await db.execute(
                    existing_statement
                )
            )

            existing = (
                existing_result
                .scalar_one_or_none()
            )

            if existing is None:

                link = (
                    ChatSessionDocument(
                        session_id=
                            session_id,

                        document_id=
                            document.id,
                    )
                )

                db.add(link)

                await db.commit()

            return document


    # =====================================================
    # SESSION DOCUMENTS
    # =====================================================

    async def get_session_documents(
        self,
        session_id,
    ):
        async with async_session_factory() as db:

            statement = (
                select(Document)

                .join(
                    ChatSessionDocument,

                    ChatSessionDocument
                    .document_id
                    == Document.id,
                )

                .where(
                    ChatSessionDocument
                    .session_id
                    == session_id
                )

                .order_by(
                    Document
                    .created_at
                    .asc()
                )
            )

            result = await db.execute(
                statement
            )

            return list(
                result
                .scalars()
                .all()
            )