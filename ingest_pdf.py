"""
Ingest một PDF từ CLI (đã sửa: bản cũ gọi PDFIngestor.ingest()
không tồn tại nên chạy là crash).

Cách dùng:
    python ingest_pdf.py [duong_dan_pdf] [tieu_de_session]

Mặc định: data/sample.pdf, session mới "CLI ingest".
Script tạo session + document rồi gọi ingest_existing(),
đúng luồng mà API đang dùng.
"""

import asyncio
import sys
import uuid

from pathlib import Path

from src.database import engine
from src.document_service import DocumentService
from src.ingest import PDFIngestor
from src.session_service import SessionService


PDF_PATH = sys.argv[1] if len(sys.argv) > 1 else "data/sample.pdf"
SESSION_TITLE = (
    sys.argv[2] if len(sys.argv) > 2 else "CLI ingest"
)


async def main():

    pdf_path = Path(PDF_PATH).resolve()

    if not pdf_path.exists():
        raise FileNotFoundError(
            f"Không tìm thấy file: {pdf_path}"
        )

    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError("File ingest phải là PDF.")

    session_service = SessionService()
    document_service = DocumentService()

    chat_session = await session_service.create_session(
        title=SESSION_TITLE
    )

    document_id = uuid.uuid4()

    document = await document_service.create_document(
        session_id=chat_session.id,
        document_id=document_id,
        name=pdf_path.name,
        storage_path=pdf_path,
        mime_type="application/pdf",
    )

    ingestor = PDFIngestor()

    try:
        result = await ingestor.ingest_existing(
            document_id=document.id,
            pdf_path=pdf_path,
        )

        print("\n" + "=" * 70)
        print("INGEST COMPLETED")
        print("=" * 70)
        print("Session ID:", chat_session.id)
        print("Document ID:", result["document_id"])
        print("Pages:", result["pages"])
        print("Chunks:", result["chunks"])
        print("Status:", result["status"])

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
