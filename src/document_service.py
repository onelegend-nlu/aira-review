from src.database import async_session_factory

from src.models import (
    ChatSession,
    ChatSessionDocument,
    Document
)


class DocumentService:

    # =====================================================
    # CREATE DOCUMENT + ATTACH TO SESSION
    # =====================================================

    async def create_document(
        self,
        session_id,
        document_id,
        name,
        storage_path,
        mime_type="application/pdf"
    ):

        async with (
            async_session_factory()
            as db
        ):

            chat_session = await db.get(
                ChatSession,
                session_id
            )


            if chat_session is None:

                raise ValueError(
                    "Không tìm thấy session."
                )


            document = Document(

                id=
                    document_id,

                name=
                    name,

                storage_path=
                    str(storage_path),

                mime_type=
                    mime_type,

                status=
                    "pending"
            )


            db.add(
                document
            )


            link = ChatSessionDocument(

                session_id=
                    session_id,

                document_id=
                    document_id
            )


            db.add(
                link
            )


            await db.commit()

            await db.refresh(
                document
            )


            return document


    # =====================================================
    # GET DOCUMENT
    # =====================================================

    async def get_document(
        self,
        document_id
    ):

        async with (
            async_session_factory()
            as db
        ):

            return await db.get(
                Document,
                document_id
            )