import uuid

from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func
)

from sqlalchemy.dialects.postgresql import (
    JSONB,
    UUID
)

from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship
)


# =========================================================
# BASE
# =========================================================

class Base(DeclarativeBase):
    pass


# =========================================================
# DOCUMENT
# =========================================================

class Document(Base):
    __tablename__ = "documents"


    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )


    name: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )


    storage_path: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )


    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="application/pdf"
    )


    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending"
    )


    page_count: Mapped[int | None] = mapped_column(
        nullable=True
    )


    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )


    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )


    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )


    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan"
    )


    sessions: Mapped[
        list["ChatSessionDocument"]
    ] = relationship(
        back_populates="document",
        cascade="all, delete-orphan"
    )


    flashcards: Mapped[
        list["Flashcard"]
    ] = relationship(
        back_populates="document",
        cascade="all, delete-orphan"
    )


# =========================================================
# CHAT SESSION
# =========================================================

class ChatSession(Base):
    __tablename__ = "chat_sessions"


    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )


    title: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )


    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )


    documents: Mapped[
        list["ChatSessionDocument"]
    ] = relationship(
        back_populates="session",
        cascade="all, delete-orphan"
    )


    messages: Mapped[
        list["ChatMessage"]
    ] = relationship(
        back_populates="session",
        cascade="all, delete-orphan"
    )


    flashcards: Mapped[
        list["Flashcard"]
    ] = relationship(
        back_populates="session",
        cascade="all, delete-orphan"
    )


# =========================================================
# CHAT SESSION <-> DOCUMENT
# =========================================================

class ChatSessionDocument(Base):
    __tablename__ = "chat_session_documents"


    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),

        ForeignKey(
            "chat_sessions.id",
            ondelete="CASCADE"
        ),

        primary_key=True
    )


    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),

        ForeignKey(
            "documents.id",
            ondelete="CASCADE"
        ),

        primary_key=True
    )


    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )


    session: Mapped["ChatSession"] = relationship(
        back_populates="documents"
    )


    document: Mapped["Document"] = relationship(
        back_populates="sessions"
    )


# =========================================================
# CHUNK
# =========================================================

class Chunk(Base):
    __tablename__ = "chunks"


    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )


    doc_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),

        ForeignKey(
            "documents.id",
            ondelete="CASCADE"
        ),

        nullable=False
    )


    page: Mapped[int] = mapped_column(
        nullable=False
    )


    text: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )


    # Project gốc có parent_text.
    # Hiện tại ta chưa sử dụng,
    # nhưng giữ schema để tiện nâng cấp.
    parent_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )


    embedding: Mapped[list[float]] = mapped_column(
        Vector(384),
        nullable=False
    )


    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )


    document: Mapped["Document"] = relationship(
        back_populates="chunks"
    )


# =========================================================
# CHAT MESSAGE
# =========================================================

class ChatMessage(Base):
    __tablename__ = "chat_messages"


    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )


    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),

        ForeignKey(
            "chat_sessions.id",
            ondelete="CASCADE"
        ),

        nullable=False
    )


    role: Mapped[str] = mapped_column(
        String(32),
        nullable=False
    )


    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )


    citations: Mapped[
        list[dict[str, Any]] | None
    ] = mapped_column(
        JSONB,
        nullable=True
    )


    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )


    session: Mapped["ChatSession"] = relationship(
        back_populates="messages"
    )


# =========================================================
# FLASHCARD
# =========================================================

class Flashcard(Base):
    __tablename__ = "flashcards"


    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )


    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),

        ForeignKey(
            "chat_sessions.id",
            ondelete="CASCADE"
        ),

        nullable=False
    )


    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),

        ForeignKey(
            "documents.id",
            ondelete="CASCADE"
        ),

        nullable=False
    )


    source_chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),

        ForeignKey(
            "chunks.id",
            ondelete="CASCADE"
        ),

        nullable=False
    )


    source_page: Mapped[int] = mapped_column(
        nullable=False
    )


    question: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )


    answer: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )


    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )


    session: Mapped["ChatSession"] = relationship(
        back_populates="flashcards"
    )


    document: Mapped["Document"] = relationship(
        back_populates="flashcards"
    )


# =========================================================
# INDEXES
# =========================================================

Index(
    "ix_chunks_doc_id",
    Chunk.doc_id
)


# HNSW cho cosine search trên embedding.
# Chỉ có tác dụng với database tạo mới bằng create_all;
# database đã tồn tại: chạy lại init_db.py hoặc
# migrations/001_hnsw_index.sql.
Index(
    "ix_chunks_embedding_hnsw",
    Chunk.embedding,
    postgresql_using="hnsw",
    postgresql_with={
        "m": 16,
        "ef_construction": 64
    },
    postgresql_ops={
        "embedding": "vector_cosine_ops"
    }
)


Index(
    "ix_chat_messages_session_id",
    ChatMessage.session_id
)

Index(
    "ix_flashcards_session_id",
    Flashcard.session_id
)


Index(
    "ix_flashcards_document_id",
    Flashcard.document_id
)
