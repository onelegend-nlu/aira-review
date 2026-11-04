import asyncio

from pathlib import Path

from sqlalchemy import delete

from src.database import async_session_factory
from src.models import Chunk, Document

from src.config import CHUNK_OVERLAP, CHUNK_SIZE
from src.parser import read_pdf
from src.chunker import chunk_pages_production
from src.embedder import Embedder


class PDFIngestor:

    def __init__(
        self,
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        embedder=None
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # Nếu API đã load Embedder rồi
        # thì dùng lại, không load model lần nữa.
        self.embedder = (
            embedder
            if embedder is not None
            else Embedder()
        )


    # =====================================================
    # INGEST DOCUMENT ĐÃ TỒN TẠI TRONG DATABASE
    # =====================================================

    async def ingest_existing(
        self,
        document_id,
        pdf_path
    ):

        pdf_path = Path(
            pdf_path
        ).resolve()


        if not pdf_path.exists():

            raise FileNotFoundError(
                f"Không tìm thấy file: "
                f"{pdf_path}"
            )


        if pdf_path.suffix.lower() != ".pdf":

            raise ValueError(
                "File ingest phải là PDF."
            )


        # =================================================
        # MARK PROCESSING
        # =================================================

        async with (
            async_session_factory()
            as db
        ):

            document = await db.get(
                Document,
                document_id
            )


            if document is None:

                raise ValueError(
                    "Không tìm thấy Document "
                    "trong database."
                )


            document.status = (
                "processing"
            )

            document.error_message = None

            await db.commit()


        try:

            # =============================================
            # PARSE PDF
            # =============================================

            print(
                f"\nReading PDF: "
                f"{pdf_path.name}"
            )


            pages = await asyncio.to_thread(
                read_pdf,
                str(pdf_path)
            )


            print(
                f"Total pages: "
                f"{len(pages)}"
            )


            # =============================================
            # CHUNK
            # =============================================

            # Chunking production đi qua một điểm vào duy
            # nhất (src.chunker.chunk_pages_production) để
            # chế độ token/sentence do src.config quyết
            # định, không rải rác ở caller.
            chunks = await asyncio.to_thread(
                chunk_pages_production,
                pages
            )


            print(
                f"Total chunks: "
                f"{len(chunks)}"
            )


            if not chunks:

                raise ValueError(
                    "Không tạo được chunk "
                    "từ PDF."
                )


            # =============================================
            # EMBEDDING
            # =============================================

            print(
                "\nCreating embeddings..."
            )


            texts = [
                chunk["text"]
                for chunk in chunks
            ]


            embeddings = (
                await asyncio.to_thread(
                    self.embedder.embed_passages,
                    texts
                )
            )


            print(
                "Embeddings completed!"
            )


            # =============================================
            # SAVE CHUNKS
            # =============================================

            async with (
                async_session_factory()
                as db
            ):

                document = await db.get(
                    Document,
                    document_id
                )


                if document is None:

                    raise ValueError(
                        "Document đã biến mất "
                        "khỏi database."
                    )


                # Nếu ingest lại document,
                # xóa chunks cũ trước.
                await db.execute(
                    delete(Chunk)
                    .where(
                        Chunk.doc_id
                        == document_id
                    )
                )


                db_chunks = []


                for (
                    chunk,
                    embedding
                ) in zip(
                    chunks,
                    embeddings
                ):

                    db_chunk = Chunk(

                        doc_id=
                            document_id,

                        page=
                            chunk["page"],

                        text=
                            chunk["text"],

                        parent_text=
                            None,

                        embedding=
                            embedding.tolist()
                    )


                    db_chunks.append(
                        db_chunk
                    )


                db.add_all(
                    db_chunks
                )


                document.page_count = (
                    len(pages)
                )

                document.status = (
                    "ready"
                )

                document.error_message = (
                    None
                )


                await db.commit()


            return {
                "document_id":
                    str(document_id),

                "pages":
                    len(pages),

                "chunks":
                    len(chunks),

                "status":
                    "ready"
            }


        except Exception as error:

            # =============================================
            # MARK FAILED
            # =============================================

            async with (
                async_session_factory()
                as db
            ):

                document = await db.get(
                    Document,
                    document_id
                )


                if document is not None:

                    document.status = (
                        "failed"
                    )

                    document.error_message = (
                        str(error)
                    )

                    await db.commit()


            raise