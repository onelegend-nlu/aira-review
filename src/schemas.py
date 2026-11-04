from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# =========================================================
# SESSION
# =========================================================

class SessionCreateRequest(BaseModel):

    title: str | None = None


class SessionResponse(BaseModel):

    id: UUID

    title: str | None = None

    created_at: datetime


# =========================================================
# DOCUMENT
# =========================================================

class DocumentResponse(BaseModel):

    id: UUID

    name: str

    status: str

    page_count: int | None = None

    error_message: str | None = None

    created_at: datetime


# =========================================================
# CHAT
# =========================================================

class ChatRequest(BaseModel):

    message: str = Field(
        min_length=1,
        max_length=8000
    )

    # Chế độ tốc độ truy xuất (tùy chọn): "lau" |
    # "trung_binh" | "nhanh" — ánh xạ sang pool rerank
    # tại RETRIEVAL_MODES trong src/config.py.
    # Thiếu hoặc không hợp lệ -> backend tự dùng chế độ
    # mặc định "lau" (pool 40, winner E7), không lỗi.
    mode: str | None = None


class CitationResponse(BaseModel):

    index: int

    chunk_id: str

    doc_id: str

    doc_name: str

    page: int

    text: str

    snippet: str

    retrieval_score: float

    rerank_score: float


class ChatResponse(BaseModel):

    session_id: UUID

    question: str

    answer: str

    citations: list[
        CitationResponse
    ]


class MessageResponse(BaseModel):

    id: UUID

    session_id: UUID

    role: str

    content: str

    citations: (
        list[dict[str, Any]]
        | None
    ) = None

    created_at: datetime


# =========================================================
# FLASHCARDS
# =========================================================

class FlashcardGenerateRequest(BaseModel):

    count: int = Field(
        default=10,
        ge=1,
        le=20
    )

    replace_existing: bool = True


class FlashcardResponse(BaseModel):

    id: UUID

    session_id: UUID

    document_id: UUID

    document_name: str

    source_chunk_id: UUID

    source_page: int

    question: str

    answer: str

    created_at: datetime


class FlashcardGenerateResponse(BaseModel):

    requested_count: int

    generated_count: int

    flashcards: list[FlashcardResponse]

