import json
import os
import re
import uuid

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID

from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    HTTPException,
    Request,
    Response,
    UploadFile,
)

from fastapi.middleware.cors import (
    CORSMiddleware,
)

from fastapi.responses import (
    JSONResponse,
    StreamingResponse,
)

from src.chat_service import ChatService
from src.config import (
    API_KEY as AIRA_API_KEY,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    MAX_UPLOAD_BYTES,
    MAX_UPLOAD_MB,
    RATE_LIMIT_PER_MIN,
    RECENT_MESSAGE_LIMIT,
    TOP_K,
    candidate_k_for_mode,
)
from src.database import engine
from src.document_service import DocumentService
from src.generator import Generator
from src.flashcard_service import FlashcardService
from src.ingest import PDFIngestor
from src.rate_limit import RateLimiter
from src.retriever import Retriever

from src.schemas import (
    ChatRequest,
    ChatResponse,
    CitationResponse,
    DocumentResponse,
    MessageResponse,
    SessionCreateRequest,
    SessionResponse,
    FlashcardGenerateRequest,
    FlashcardGenerateResponse,
    FlashcardResponse,
)

from src.session_service import (
    SessionService,
)


# =========================================================
# CONFIG
# =========================================================

# Pool rerank theo chế độ tốc độ (candidate_k_for_mode) /
# TOP_K / RECENT_MESSAGE_LIMIT / giới hạn upload lấy từ
# src.config (một nguồn duy nhất).

UPLOAD_DIR = Path(
    "data/uploads"
).resolve()

INSUFFICIENT_ANSWER = (
    "Không tìm thấy đủ thông tin trong tài liệu."
)


# =========================================================
# SERVICES
# =========================================================

session_service = SessionService()
chat_service = ChatService()
document_service = DocumentService()
flashcard_service = FlashcardService()


# =========================================================
# SSE
# =========================================================

def sse(
    event,
    data,
):
    json_data = json.dumps(
        data,
        ensure_ascii=False,
    )

    return (
        f"event: {event}\n"
        f"data: {json_data}\n\n"
    )


# =========================================================
# INSUFFICIENT ANSWER
# =========================================================

def is_insufficient_answer(
    answer: str,
) -> bool:

    normalized_answer = " ".join(
        answer
        .strip()
        .lower()
        .split()
    )

    normalized_target = " ".join(
        INSUFFICIENT_ANSWER
        .lower()
        .split()
    )

    return (
        normalized_answer
        .startswith(
            normalized_target
        )
    )


# =========================================================
# CITATION COVERAGE
# =========================================================

def citation_coverage(
    answer,
    citations,
):
    if not citations:
        return 0.0

    matches = re.findall(
        r"\[(\d+)\]",
        answer,
    )

    if not matches:
        return 0.0

    valid_indexes = {
        citation["index"]
        for citation
        in citations
    }

    used_indexes = [
        int(value)
        for value
        in matches
    ]

    valid_count = sum(
        1
        for index in used_indexes
        if index in valid_indexes
    )

    return (
        valid_count
        /
        len(used_indexes)
    )


# =========================================================
# PDF NAME
# =========================================================

def safe_pdf_name(
    filename,
):
    name = Path(
        filename
        or "upload.pdf"
    ).name

    if not name.lower().endswith(
        ".pdf"
    ):
        raise HTTPException(
            status_code=400,
            detail=
                "Chỉ hỗ trợ file PDF.",
        )

    return name


# =========================================================
# BUILD CITATIONS
# =========================================================

def build_citations(
    results,
):
    citations = []

    for i, result in enumerate(
        results,
        start=1,
    ):
        text = result["text"]

        snippet = (
            text[:250] + "..."
            if len(text) > 250
            else text
        )

        citations.append({
            "index":
                i,

            "chunk_id":
                result["chunk_id"],

            "doc_id":
                result["document_id"],

            "doc_name":
                result["document_name"],

            "page":
                result["page"],

            "text":
                text,

            "snippet":
                snippet,

            "retrieval_score":
                result[
                    "retrieval_score"
                ],

            "rerank_score":
                result[
                    "rerank_score"
                ],
        })

    return citations


# =========================================================
# BACKGROUND INGEST
# =========================================================

async def _run_ingest_background(
    ingestor,
    document_id,
    storage_path,
):
    """Chạy ingest ngoài request/response cycle.

    ingest_existing() tự ghi status processing/ready/failed
    vào database nên endpoint upload chỉ cần trả về ngay;
    frontend poll trạng thái document cho tới khi ready.
    """

    try:
        await ingestor.ingest_existing(
            document_id=document_id,
            pdf_path=storage_path,
        )

    except Exception as error:
        print(
            "Document ingest failed:",
            error,
        )


# =========================================================
# LIFESPAN
# =========================================================

@asynccontextmanager
async def lifespan(
    app: FastAPI,
):
    print(
        "Loading AIRA RAG models..."
    )

    app.state.retriever = (
        Retriever()
    )

    app.state.generator = (
        Generator()
    )

    app.state.ingestor = (
        PDFIngestor(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,

            embedder=
                app.state
                .retriever
                .embedder,
        )
    )

    UPLOAD_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        "AIRA API started."
    )

    yield

    print(
        "Closing database connections..."
    )

    await engine.dispose()


# =========================================================
# APP
# =========================================================

app = FastAPI(
    title="AIRA API",
    version="0.7.0",
    lifespan=lifespan,
)


# =========================================================
# AUTH (tùy chọn, bật bằng AIRA_API_KEY trong .env)
# =========================================================

@app.middleware("http")
async def require_api_key(request: Request, call_next):

    # Chưa đặt key -> tắt auth (chạy local).
    # Route hệ thống (/ và /health) luôn mở.
    if (
        AIRA_API_KEY
        and request.method != "OPTIONS"
        and request.url.path.startswith("/api/")
        and request.headers.get("x-api-key")
            != AIRA_API_KEY
    ):
        return JSONResponse(
            status_code=401,
            content={
                "detail":
                    "Thiếu hoặc sai X-API-Key."
            },
        )

    return await call_next(request)


# =========================================================
# RATE LIMIT (nhẹ, chống spam đốt quota trên bản demo)
# =========================================================

rate_limiter = RateLimiter(
    RATE_LIMIT_PER_MIN
)


def _is_rate_limited_route(
    request: Request,
) -> bool:
    """Chỉ giới hạn POST chat và POST upload tài liệu."""

    if request.method != "POST":
        return False

    path = request.url.path

    if not path.startswith(
        "/api/v1/sessions/"
    ):
        return False

    return (
        path.endswith("/chat")
        or path.endswith("/chat/stream")
        or path.endswith("/documents")
    )


@app.middleware("http")
async def rate_limit(request: Request, call_next):

    # RATE_LIMIT_PER_MIN = 0 -> tắt (RateLimiter.allow
    # luôn True) nên không cần rẽ nhánh riêng ở đây.
    if _is_rate_limited_route(request):

        client_ip = (
            request.client.host
            if request.client
            else "unknown"
        )

        if not rate_limiter.allow(client_ip):
            return JSONResponse(
                status_code=429,
                content={
                    "detail":
                        "Bạn đang gửi yêu cầu quá "
                        "nhanh. Vui lòng đợi khoảng "
                        "một phút rồi thử lại."
                },
            )

    return await call_next(request)


# =========================================================
# CORS
# =========================================================

# Origin được phép gọi API từ trình duyệt, đọc từ biến môi
# trường AIRA_CORS_ORIGINS (danh sách phân tách bằng dấu phẩy).
# Khi env không đặt, mặc định chỉ gồm hai origin local của
# frontend để chạy local giữ nguyên hành vi như trước.
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "AIRA_CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,

    allow_origins=CORS_ORIGINS,

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)


# =========================================================
# SYSTEM
# =========================================================

@app.get(
    "/",
    tags=["system"],
)
async def root():
    return {
        "name": "AIRA",
        "full_name":
            "AI Retrieval Assistant",
        "status": "running",
    }


@app.get(
    "/health",
    tags=["system"],
)
async def health():
    return {
        "status": "ok"
    }


# =========================================================
# CREATE SESSION
# =========================================================

@app.post(
    "/api/v1/sessions",

    response_model=
        SessionResponse,

    tags=["sessions"],
)
async def create_session(
    payload:
        SessionCreateRequest,
):
    chat_session = (
        await session_service
        .create_session(
            title=
                payload.title
        )
    )

    return SessionResponse(
        id=
            chat_session.id,

        title=
            chat_session.title,

        created_at=
            chat_session.created_at,
    )


# =========================================================
# LIST SESSIONS
# =========================================================

@app.get(
    "/api/v1/sessions",

    response_model=
        list[SessionResponse],

    tags=["sessions"],
)
async def list_sessions():
    sessions = (
        await session_service
        .list_sessions()
    )

    return [
        SessionResponse(
            id=item.id,

            title=item.title,

            created_at=
                item.created_at,
        )

        for item in sessions
    ]


# =========================================================
# LATEST SESSION
# =========================================================

@app.get(
    "/api/v1/sessions/latest",

    response_model=
        SessionResponse,

    tags=["sessions"],
)
async def get_latest_session():

    item = (
        await session_service
        .get_latest_session()
    )

    if item is None:
        raise HTTPException(
            status_code=404,
            detail=
                "Chưa có session.",
        )

    return SessionResponse(
        id=item.id,
        title=item.title,
        created_at=item.created_at,
    )


# =========================================================
# GET SESSION
# =========================================================

@app.get(
    "/api/v1/sessions/{session_id}",

    response_model=
        SessionResponse,

    tags=["sessions"],
)
async def get_session(
    session_id: UUID,
):
    item = (
        await session_service
        .get_session_by_id(
            session_id
        )
    )

    if item is None:
        raise HTTPException(
            status_code=404,
            detail=
                "Không tìm thấy session.",
        )

    return SessionResponse(
        id=item.id,
        title=item.title,
        created_at=item.created_at,
    )


# =========================================================
# DELETE SESSION
# =========================================================

@app.delete(
    "/api/v1/sessions/{session_id}",

    status_code=204,

    tags=["sessions"],
)
async def delete_session(
    session_id: UUID,
):
    deleted = (
        await session_service
        .delete_session(
            session_id
        )
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=
                "Không tìm thấy session.",
        )

    return Response(
        status_code=204
    )


# =========================================================
# UPLOAD DOCUMENT
# =========================================================

@app.post(
    "/api/v1/sessions/{session_id}/documents",

    response_model=
        DocumentResponse,

    tags=["documents"],
)
async def upload_document(
    session_id: UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    chat_session = (
        await session_service
        .get_session_by_id(
            session_id
        )
    )

    if chat_session is None:
        raise HTTPException(
            status_code=404,
            detail=
                "Không tìm thấy session.",
        )

    safe_name = (
        safe_pdf_name(
            file.filename
        )
    )

    if (
        file.content_type
        and
        file.content_type
        != "application/pdf"
    ):
        raise HTTPException(
            status_code=400,
            detail=
                "Chỉ hỗ trợ file PDF.",
        )

    document_id = (
        uuid.uuid4()
    )

    storage_path = (
        UPLOAD_DIR
        /
        f"{document_id}-{safe_name}"
    )

    # Ghi file theo từng đoạn và đếm dung lượng:
    # vượt giới hạn -> xóa file dở, trả 413.
    # (Bản cũ copyfileobj không giới hạn kích thước.)
    total_bytes = 0

    try:
        with storage_path.open(
            "wb"
        ) as output:

            while True:
                chunk = await file.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                total_bytes += len(chunk)

                if total_bytes > MAX_UPLOAD_BYTES:
                    output.close()
                    storage_path.unlink(
                        missing_ok=True
                    )

                    raise HTTPException(
                        status_code=413,
                        detail=(
                            "File vượt quá giới hạn "
                            f"{MAX_UPLOAD_MB:g} MB."
                        ),
                    )

                output.write(chunk)

    finally:
        await file.close()

    if total_bytes == 0:
        storage_path.unlink(
            missing_ok=True
        )

        raise HTTPException(
            status_code=400,
            detail="File rỗng.",
        )

    try:
        document = (
            await document_service
            .create_document(
                session_id=
                    session_id,

                document_id=
                    document_id,

                name=
                    safe_name,

                storage_path=
                    storage_path,

                mime_type=
                    "application/pdf",
            )
        )

    except Exception:
        if storage_path.exists():
            storage_path.unlink()

        raise

    # Ingest chạy nền: response trả về ngay với
    # status hiện tại (pending), frontend poll cho
    # tới khi document ready/failed.
    background_tasks.add_task(
        _run_ingest_background,
        request.app.state.ingestor,
        document.id,
        storage_path,
    )

    document = (
        await document_service
        .get_document(
            document.id
        )
    )

    return DocumentResponse(
        id=document.id,
        name=document.name,

        status=
            document.status,

        page_count=
            document.page_count,

        error_message=
            document.error_message,

        created_at=
            document.created_at,
    )


# =========================================================
# GET DOCUMENT
# =========================================================

@app.get(
    "/api/v1/documents/{document_id}",

    response_model=
        DocumentResponse,

    tags=["documents"],
)
async def get_document(
    document_id: UUID,
):
    document = (
        await document_service
        .get_document(
            document_id
        )
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail=
                "Không tìm thấy document.",
        )

    return DocumentResponse(
        id=document.id,
        name=document.name,

        status=
            document.status,

        page_count=
            document.page_count,

        error_message=
            document.error_message,

        created_at=
            document.created_at,
    )


# =========================================================
# SESSION DOCUMENTS
# =========================================================

@app.get(
    "/api/v1/sessions/{session_id}/documents",

    response_model=
        list[DocumentResponse],

    tags=["documents"],
)
async def get_session_documents(
    session_id: UUID,
):
    chat_session = (
        await session_service
        .get_session_by_id(
            session_id
        )
    )

    if chat_session is None:
        raise HTTPException(
            status_code=404,
            detail=
                "Không tìm thấy session.",
        )

    documents = (
        await session_service
        .get_session_documents(
            session_id
        )
    )

    return [
        DocumentResponse(
            id=document.id,
            name=document.name,

            status=
                document.status,

            page_count=
                document.page_count,

            error_message=
                document.error_message,

            created_at=
                document.created_at,
        )

        for document in documents
    ]


# =========================================================
# FLASHCARDS - GENERATE
# =========================================================

@app.post(
    "/api/v1/sessions/{session_id}/flashcards/generate",

    response_model=
        FlashcardGenerateResponse,

    tags=["flashcards"],
)
async def generate_flashcards(
    session_id: UUID,
    payload: FlashcardGenerateRequest,
    request: Request,
):
    chat_session = (
        await session_service
        .get_session_by_id(
            session_id
        )
    )

    if chat_session is None:
        raise HTTPException(
            status_code=404,
            detail=
                "Không tìm thấy session.",
        )

    documents = (
        await session_service
        .get_session_documents(
            session_id
        )
    )

    ready_documents = [
        document
        for document in documents
        if document.status == "ready"
    ]

    if not ready_documents:
        raise HTTPException(
            status_code=400,
            detail=
                "Session chưa có tài liệu ready.",
        )

    generator = (
        request.app.state.generator
    )

    try:
        cards = (
            await flashcard_service
            .generate_flashcards(
                session_id=
                    session_id,

                generator=
                    generator,

                count=
                    payload.count,

                replace_existing=
                    payload.replace_existing,
            )
        )

    except Exception as error:
        print(
            "Flashcard generation failed:",
            error,
        )

        raise HTTPException(
            status_code=503,
            detail=
                "Không thể tạo flashcard lúc này.",
        ) from error

    return FlashcardGenerateResponse(
        requested_count=
            payload.count,

        generated_count=
            len(cards),

        flashcards=[
            FlashcardResponse(**card)
            for card in cards
        ],
    )


# =========================================================
# FLASHCARDS - LIST
# =========================================================

@app.get(
    "/api/v1/sessions/{session_id}/flashcards",

    response_model=
        list[FlashcardResponse],

    tags=["flashcards"],
)
async def list_flashcards(
    session_id: UUID,
):
    chat_session = (
        await session_service
        .get_session_by_id(
            session_id
        )
    )

    if chat_session is None:
        raise HTTPException(
            status_code=404,
            detail=
                "Không tìm thấy session.",
        )

    cards = (
        await flashcard_service
        .list_flashcards(
            session_id
        )
    )

    return [
        FlashcardResponse(**card)
        for card in cards
    ]


# =========================================================
# FLASHCARDS - DELETE ONE
# =========================================================

@app.delete(
    "/api/v1/sessions/{session_id}/flashcards/{flashcard_id}",

    status_code=204,

    tags=["flashcards"],
)
async def delete_flashcard(
    session_id: UUID,
    flashcard_id: UUID,
):
    chat_session = (
        await session_service
        .get_session_by_id(
            session_id
        )
    )

    if chat_session is None:
        raise HTTPException(
            status_code=404,
            detail=
                "Không tìm thấy session.",
        )

    deleted = (
        await flashcard_service
        .delete_flashcard(
            session_id=
                session_id,

            flashcard_id=
                flashcard_id,
        )
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=
                "Không tìm thấy flashcard.",
        )

    return Response(
        status_code=204
    )


# =========================================================
# CHAT JSON
# =========================================================

@app.post(
    "/api/v1/sessions/{session_id}/chat",

    response_model=
        ChatResponse,

    tags=["chat"],
)
async def chat(
    session_id: UUID,
    payload: ChatRequest,
    request: Request,
):
    chat_session = (
        await session_service
        .get_session_by_id(
            session_id
        )
    )

    if chat_session is None:
        raise HTTPException(
            status_code=404,
            detail=
                "Không tìm thấy session.",
        )

    documents = (
        await session_service
        .get_session_documents(
            session_id
        )
    )

    ready_documents = [
        document
        for document in documents
        if document.status
        == "ready"
    ]

    if not ready_documents:
        raise HTTPException(
            status_code=400,
            detail=
                "Session chưa có tài liệu ready.",
        )

    recent_messages = (
        await chat_service
        .get_recent_messages(
            session_id=
                session_id,

            limit=
                RECENT_MESSAGE_LIMIT,
        )
    )

    # Câu hỏi đầu tiên:
    # tự đặt title session.
    if not recent_messages:
        await session_service \
            .auto_title_if_default(
                session_id=
                    session_id,

                first_message=
                    payload.message,
            )

    await chat_service.save_message(
        session_id=session_id,
        role="user",
        content=payload.message,
    )

    # Chế độ tốc độ của request (thiếu/không hợp lệ ->
    # mặc định "lau", pool 40 = winner E7).
    candidate_k = candidate_k_for_mode(
        payload.mode
    )

    retriever = (
        request.app.state.retriever
    )

    results = (
        await retriever.search(
            session_id=
                session_id,

            query=
                payload.message,

            recent_messages=
                recent_messages,

            candidate_k=
                candidate_k,

            top_k=
                TOP_K,
        )
    )

    if not results:
        answer = (
            INSUFFICIENT_ANSWER
        )

        citations = []

    else:
        generator = (
            request.app.state.generator
        )

        answer = (
            await generator.generate(
                query=
                    payload.message,

                retrieved_chunks=
                    results,

                recent_messages=
                    recent_messages,
            )
        )

        citations = (
            build_citations(
                results
            )
        )

        if is_insufficient_answer(
            answer
        ):
            citations = []

    await chat_service.save_message(
        session_id=session_id,
        role="assistant",
        content=answer,
        citations=citations,
    )

    return ChatResponse(
        session_id=session_id,

        question=
            payload.message,

        answer=answer,

        citations=[
            CitationResponse(
                **citation
            )
            for citation
            in citations
        ],
    )


# =========================================================
# CHAT STREAM
# =========================================================

@app.post(
    "/api/v1/sessions/{session_id}/chat/stream",

    tags=["chat"],
)
async def chat_stream(
    session_id: UUID,
    payload: ChatRequest,
    request: Request,
):
    chat_session = (
        await session_service
        .get_session_by_id(
            session_id
        )
    )

    if chat_session is None:
        raise HTTPException(
            status_code=404,
            detail=
                "Không tìm thấy session.",
        )

    documents = (
        await session_service
        .get_session_documents(
            session_id
        )
    )

    ready_documents = [
        document
        for document in documents
        if document.status
        == "ready"
    ]

    if not ready_documents:
        raise HTTPException(
            status_code=400,
            detail=
                "Session chưa có tài liệu ready.",
        )

    recent_messages = (
        await chat_service
        .get_recent_messages(
            session_id=
                session_id,

            limit=
                RECENT_MESSAGE_LIMIT,
        )
    )

    # Auto title từ câu hỏi đầu.
    if not recent_messages:
        await session_service \
            .auto_title_if_default(
                session_id=
                    session_id,

                first_message=
                    payload.message,
            )

    await chat_service.save_message(
        session_id=session_id,
        role="user",
        content=payload.message,
    )

    # Chế độ tốc độ của request (thiếu/không hợp lệ ->
    # mặc định "lau", pool 40 = winner E7).
    candidate_k = candidate_k_for_mode(
        payload.mode
    )

    async def events() -> AsyncIterator[str]:

        answer_parts = []
        citations = []

        try:
            retriever = (
                request.app
                .state
                .retriever
            )

            results = (
                await retriever.search(
                    session_id=
                        session_id,

                    query=
                        payload.message,

                    recent_messages=
                        recent_messages,

                    candidate_k=
                        candidate_k,

                    top_k=
                        TOP_K,
                )
            )

            if not results:

                text = (
                    INSUFFICIENT_ANSWER
                )

                answer_parts.append(
                    text
                )

                yield sse(
                    "token",
                    {
                        "text": text
                    },
                )

            else:
                citations = (
                    build_citations(
                        results
                    )
                )

                generator = (
                    request.app
                    .state
                    .generator
                )

                async for token in (
                    generator
                    .stream_generate(
                        query=
                            payload.message,

                        retrieved_chunks=
                            results,

                        recent_messages=
                            recent_messages,
                    )
                ):
                    answer_parts.append(
                        token
                    )

                    yield sse(
                        "token",
                        {
                            "text":
                                token
                        },
                    )

            answer = "".join(
                answer_parts
            )

            if is_insufficient_answer(
                answer
            ):
                citations = []

            await chat_service \
                .save_message(
                    session_id=
                        session_id,

                    role=
                        "assistant",

                    content=
                        answer,

                    citations=
                        citations,
                )

            coverage = (
                citation_coverage(
                    answer=
                        answer,

                    citations=
                        citations,
                )
            )

            yield sse(
                "citations",
                {
                    "citations":
                        citations,

                    "citation_coverage":
                        coverage,
                },
            )

            yield sse(
                "done",
                {},
            )

        except Exception as error:

            # Chi tiết lỗi chỉ ghi log phía server; client
            # chỉ nhận thông điệp chung, không lộ str(error)
            # (tránh rò thông tin nội bộ qua sự kiện SSE).
            print(
                "Streaming error:",
                error,
            )

            yield sse(
                "error",
                {
                    "message":
                        "Đã xảy ra lỗi khi xử lý "
                        "yêu cầu. Vui lòng thử lại."
                },
            )

    return StreamingResponse(
        events(),

        media_type=
            "text/event-stream",

        headers={
            "Cache-Control":
                "no-cache",

            "Connection":
                "keep-alive",

            "X-Accel-Buffering":
                "no",
        },
    )


# =========================================================
# CHAT HISTORY
# =========================================================

@app.get(
    "/api/v1/sessions/{session_id}/messages",

    response_model=
        list[MessageResponse],

    tags=["chat"],
)
async def get_messages(
    session_id: UUID,
):
    chat_session = (
        await session_service
        .get_session_by_id(
            session_id
        )
    )

    if chat_session is None:
        raise HTTPException(
            status_code=404,
            detail=
                "Không tìm thấy session.",
        )

    messages = (
        await chat_service
        .get_messages(
            session_id
        )
    )

    return [
        MessageResponse(
            id=message.id,

            session_id=
                message.session_id,

            role=
                message.role,

            content=
                message.content,

            citations=
                message.citations,

            created_at=
                message.created_at,
        )

        for message in messages
    ]