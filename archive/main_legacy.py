import asyncio

from src.chat_service import ChatService
from src.database import engine
from src.generator import Generator
from src.retriever import Retriever
from src.session_service import SessionService


# =========================================================
# CONFIG
# =========================================================

CANDIDATE_K = 10  # khớp api.py / src.config
TOP_K = 5

RECENT_MESSAGE_LIMIT = 3


# =========================================================
# BUILD CITATIONS
# =========================================================

def build_citations(
    results
):

    citations = []


    for i, result in enumerate(
        results,
        start=1
    ):

        citations.append({

            "index":
                i,

            "chunk_id":
                result["chunk_id"],

            "document_id":
                result["document_id"],

            "doc_name":
                result["document_name"],

            "page":
                result["page"],

            "text":
                result["text"],

            "retrieval_score":
                result[
                    "retrieval_score"
                ],

            "rerank_score":
                result[
                    "rerank_score"
                ]
        })


    return citations


# =========================================================
# MAIN
# =========================================================

async def main():

    try:

        print(
            "=" * 70
        )

        print(
            "RAG LEARNING ASSISTANT"
        )

        print(
            "=" * 70
        )


        # =================================================
        # SERVICES
        # =================================================

        session_service = (
            SessionService()
        )

        chat_service = (
            ChatService()
        )


        # =================================================
        # ACTIVE SESSION
        # =================================================

        chat_session = (
            await session_service
            .get_latest_session()
        )


        if chat_session is None:

            print(
                "\nChưa có chat session."
            )

            print(
                "Hãy chạy:"
            )

            print(
                "python create_session.py"
            )

            return


        print(
            "\nActive session:"
        )

        print(
            f"ID: "
            f"{chat_session.id}"
        )

        print(
            f"Title: "
            f"{chat_session.title}"
        )


        # =================================================
        # DOCUMENTS
        # =================================================

        documents = (
            await session_service
            .get_session_documents(
                chat_session.id
            )
        )


        if not documents:

            print(
                "\nSession này "
                "chưa có tài liệu."
            )

            return


        print(
            "\nDocuments:"
        )


        for document in documents:

            print(
                f"- {document.name}"
            )


        # =================================================
        # LOAD MODELS ONCE
        # =================================================

        print()


        retriever = Retriever()

        generator = Generator()


        # =================================================
        # CHAT LOOP
        # =================================================

        print(
            "\n"
            + "-" * 70
        )

        print(
            "Chat đã sẵn sàng."
        )

        print(
            "Gõ 'exit' hoặc 'quit' "
            "để thoát."
        )

        print(
            "-" * 70
        )


        while True:

            # =============================================
            # QUESTION
            # =============================================

            query = input(
                "\nQuestion: "
            ).strip()


            if not query:

                continue


            if query.lower() in {
                "exit",
                "quit"
            }:

                print(
                    "\nGoodbye!"
                )

                break


            # =============================================
            # GET HISTORY BEFORE CURRENT QUESTION
            # =============================================

            recent_messages = (
                await chat_service
                .get_recent_messages(

                    session_id=
                        chat_session.id,

                    limit=
                        RECENT_MESSAGE_LIMIT
                )
            )


            # =============================================
            # SAVE CURRENT USER MESSAGE
            # =============================================

            await chat_service.save_message(

                session_id=
                    chat_session.id,

                role=
                    "user",

                content=
                    query
            )


            # =============================================
            # RETRIEVAL
            # =============================================

            print(
                "\nSearching "
                "session documents..."
            )


            results = (
                await retriever.search(

                    session_id=
                        chat_session.id,

                    query=
                        query,

                    recent_messages=
                        recent_messages,

                    candidate_k=
                        CANDIDATE_K,

                    top_k=
                        TOP_K
                )
            )


            # =============================================
            # NO RESULTS
            # =============================================

            if not results:

                answer = (
                    "Không tìm thấy đủ "
                    "thông tin trong tài liệu."
                )


                print(
                    "\n"
                    + "=" * 70
                )

                print(
                    "ANSWER"
                )

                print(
                    "=" * 70
                )

                print(
                    answer
                )


                await chat_service.save_message(

                    session_id=
                        chat_session.id,

                    role=
                        "assistant",

                    content=
                        answer,

                    citations=
                        []
                )


                continue


            # =============================================
            # SHOW CONTEXT
            # =============================================

            print(
                "\nRetrieved + "
                "reranked context:"
            )


            for i, result in enumerate(
                results,
                start=1
            ):

                print(
                    "\n"
                    + "=" * 70
                )


                print(
                    f"[{i}] "
                    f"{result['document_name']} "
                    f"| Page "
                    f"{result['page']}"
                )


                print(
                    f"Dense score: "
                    f"{result['retrieval_score']:.4f}"
                )


                print(
                    f"Rerank score: "
                    f"{result['rerank_score']:.4f}"
                )


                print(
                    result["text"]
                )


            # =============================================
            # GENERATE
            # =============================================

            answer = (
                await generator.generate(

                    query=
                        query,

                    retrieved_chunks=
                        results,

                    recent_messages=
                        recent_messages
                )
            )


            # =============================================
            # CITATIONS
            # =============================================

            citations = (
                build_citations(
                    results
                )
            )


            # =============================================
            # SAVE ASSISTANT MESSAGE
            # =============================================

            await chat_service.save_message(

                session_id=
                    chat_session.id,

                role=
                    "assistant",

                content=
                    answer,

                citations=
                    citations
            )


            # =============================================
            # ANSWER
            # =============================================

            print(
                "\n"
                + "=" * 70
            )

            print(
                "ANSWER"
            )

            print(
                "=" * 70
            )


            print(
                answer
            )


            # =============================================
            # SOURCES
            # =============================================

            print(
                "\n"
                + "=" * 70
            )

            print(
                "SOURCES"
            )

            print(
                "=" * 70
            )


            for i, result in enumerate(
                results,
                start=1
            ):

                print(
                    f"[{i}] "
                    f"{result['document_name']} "
                    f"| Page "
                    f"{result['page']} "
                    f"| Dense: "
                    f"{result['retrieval_score']:.4f} "
                    f"| Rerank: "
                    f"{result['rerank_score']:.4f}"
                )


    finally:

        await engine.dispose()


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":

    asyncio.run(
        main()
    )