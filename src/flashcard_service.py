from sqlalchemy import delete, select

from src.database import async_session_factory
from src.models import (
    ChatSessionDocument,
    Chunk,
    Document,
    Flashcard,
)


MAX_SOURCE_ROWS = 200
MAX_SOURCE_CHUNKS = 40


def _normalize_question(
    value: str,
) -> str:
    return " ".join(
        value.lower().split()
    )


def _evenly_sample(
    rows,
    limit: int,
):
    if len(rows) <= limit:
        return list(rows)

    if limit <= 1:
        return [rows[0]]

    indexes = []

    for i in range(limit):
        index = round(
            i * (len(rows) - 1)
            / (limit - 1)
        )

        if index not in indexes:
            indexes.append(index)

    return [
        rows[index]
        for index in indexes
    ]


class FlashcardService:

    # =====================================================
    # SOURCE CHUNKS
    # =====================================================

    async def get_source_chunks(
        self,
        session_id,
    ):
        async with async_session_factory() as db:

            statement = (
                select(
                    Chunk,
                    Document,
                )

                .join(
                    Document,
                    Document.id
                    == Chunk.doc_id,
                )

                .join(
                    ChatSessionDocument,
                    ChatSessionDocument.document_id
                    == Document.id,
                )

                .where(
                    ChatSessionDocument.session_id
                    == session_id
                )

                .where(
                    Document.status
                    == "ready"
                )

                .order_by(
                    Document.created_at.asc(),
                    Chunk.page.asc(),
                    Chunk.created_at.asc(),
                )

                .limit(MAX_SOURCE_ROWS)
            )

            rows = (
                await db.execute(
                    statement
                )
            ).all()

        sampled_rows = _evenly_sample(
            rows,
            MAX_SOURCE_CHUNKS,
        )

        return [
            {
                "source_index": index,
                "chunk_id": chunk.id,
                "document_id": document.id,
                "document_name": document.name,
                "page": chunk.page,
                "text": chunk.text,
            }
            for index, (chunk, document)
            in enumerate(
                sampled_rows,
                start=1,
            )
        ]


    # =====================================================
    # GENERATE + SAVE
    # =====================================================

    async def generate_flashcards(
        self,
        session_id,
        generator,
        count: int = 10,
        replace_existing: bool = True,
    ):
        source_chunks = (
            await self.get_source_chunks(
                session_id
            )
        )

        if not source_chunks:
            return []

        generated = (
            await generator.generate_flashcards(
                source_chunks=
                    source_chunks,
                count=count,
            )
        )

        source_map = {
            item["source_index"]: item
            for item in source_chunks
        }

        valid_cards = []
        seen_questions = set()

        for item in generated:

            source = source_map.get(
                item["source_index"]
            )

            if source is None:
                continue

            normalized = _normalize_question(
                item["question"]
            )

            if (
                not normalized
                or normalized
                in seen_questions
            ):
                continue

            seen_questions.add(
                normalized
            )

            valid_cards.append((
                item,
                source,
            ))

            if len(valid_cards) >= count:
                break

        if not valid_cards:
            return []

        async with async_session_factory() as db:

            if replace_existing:
                await db.execute(
                    delete(Flashcard)
                    .where(
                        Flashcard.session_id
                        == session_id
                    )
                )

            cards = []

            for item, source in valid_cards:

                card = Flashcard(
                    session_id=
                        session_id,

                    document_id=
                        source[
                            "document_id"
                        ],

                    source_chunk_id=
                        source[
                            "chunk_id"
                        ],

                    source_page=
                        source["page"],

                    question=
                        item["question"],

                    answer=
                        item["answer"],
                )

                db.add(card)
                cards.append(card)

            await db.commit()

            for card in cards:
                await db.refresh(card)

        return await self.list_flashcards(
            session_id
        )


    # =====================================================
    # LIST
    # =====================================================

    async def list_flashcards(
        self,
        session_id,
    ):
        async with async_session_factory() as db:

            statement = (
                select(
                    Flashcard,
                    Document.name,
                )

                .join(
                    Document,
                    Document.id
                    == Flashcard.document_id,
                )

                .where(
                    Flashcard.session_id
                    == session_id
                )

                .order_by(
                    Flashcard.created_at.asc(),
                    Flashcard.id.asc(),
                )
            )

            rows = (
                await db.execute(
                    statement
                )
            ).all()

            return [
                {
                    "id": card.id,
                    "session_id": card.session_id,
                    "document_id": card.document_id,
                    "document_name": document_name,
                    "source_chunk_id": card.source_chunk_id,
                    "source_page": card.source_page,
                    "question": card.question,
                    "answer": card.answer,
                    "created_at": card.created_at,
                }
                for card, document_name
                in rows
            ]


    # =====================================================
    # DELETE ONE
    # =====================================================

    async def delete_flashcard(
        self,
        session_id,
        flashcard_id,
    ) -> bool:
        async with async_session_factory() as db:

            statement = (
                delete(Flashcard)

                .where(
                    Flashcard.id
                    == flashcard_id
                )

                .where(
                    Flashcard.session_id
                    == session_id
                )
            )

            result = await db.execute(
                statement
            )

            await db.commit()

            return bool(
                result.rowcount
            )
