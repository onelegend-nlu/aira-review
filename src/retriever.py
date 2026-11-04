import asyncio
import re
import unicodedata

from sqlalchemy import select

from src import config
from src.bm25 import BM25Index, rrf_fuse
from src.database import async_session_factory
from src.embedder import Embedder
from src.models import (
    ChatSessionDocument,
    Chunk,
    Document
)
from src.reranker import Reranker


class Retriever:

    def __init__(self):

        self.embedder = Embedder()

        self.reranker = Reranker()

        # Cache BM25 theo session: {session_id: (số chunk,
        # BM25Index, universe)}. Invalidate khi số chunk
        # của session thay đổi (thêm/xóa tài liệu).
        self._bm25_cache = {}


    # =====================================================
    # FOLLOW-UP DETECTION
    # =====================================================

    @staticmethod
    def normalize_for_follow_up_detection(
        text
    ):

        text = (
            text
            or ""
        ).lower()

        text = unicodedata.normalize(
            "NFD",
            text
        )

        text = "".join(
            char
            for char in text
            if unicodedata.category(char)
            != "Mn"
        )

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text.strip()


    def needs_conversation_context(
        self,
        query,
        recent_messages=None
    ):

        # Không có history thì chắc chắn
        # không cần contextual retrieval.
        if not recent_messages:
            return False


        normalized = (
            self.normalize_for_follow_up_detection(
                query
            )
        )


        if not normalized:
            return False


        # -------------------------------------------------
        # 1. Đại từ / cụm tham chiếu rõ ràng
        # -------------------------------------------------

        reference_phrases = [

            "cai do",
            "cai nay",
            "dieu do",
            "dieu nay",

            "phan do",
            "phan nay",
            "phan tren",
            "o tren",
            "ben tren",

            "cau tren",
            "y tren",
            "y do",
            "y nay",

            "truong hop do",
            "truong hop nay",

            "vi du do",
            "vi du nay",

            "tai lieu do",
            "tai lieu nay",

            "mo hinh do",
            "mo hinh nay",

            "phuong phap do",
            "phuong phap nay",

            "thuat toan do",
            "thuat toan nay",

            "khai niem do",
            "khai niem nay",

            "loai do",
            "loai nay",
            "loai thu",

            "cai thu",
            "phan thu",
        ]


        if any(
            phrase in normalized
            for phrase
            in reference_phrases
        ):
            return True


        # "nó" / "no" đứng như một từ riêng.
        if re.search(
            r"\bno\b",
            normalized
        ):
            return True


        # -------------------------------------------------
        # 2. Follow-up mở đầu rõ ràng
        # -------------------------------------------------

        follow_up_prefixes = (

            "vay con ",
            "the con ",

            "vay no ",
            "the no ",

            "vay cai ",
            "the cai ",

            "con cai ",
            "con phan ",
            "con dieu ",

            "tiep theo ",
        )


        if normalized.startswith(
            follow_up_prefixes
        ):
            return True


        # -------------------------------------------------
        # 3. Câu rút gọn chỉ có ý nghĩa nhờ history
        # -------------------------------------------------

        short_follow_up_patterns = [

            r"^(tai sao|vi sao)\??$",

            r"^(nhu the nao|the nao)\??$",

            r"^(cu the hon|noi ro hon|giai thich them)\??$",

            r"^(co gi khac|con gi nua)\??$",

            r"^con .* (thi sao|the nao)\??$",
        ]


        if any(
            re.match(
                pattern,
                normalized
            )
            for pattern
            in short_follow_up_patterns
        ):
            return True


        # Mặc định: câu hỏi độc lập.
        return False


    # =====================================================
    # BUILD CONTEXT-AWARE RETRIEVAL QUERY
    # =====================================================

    def build_contextual_query(
        self,
        query,
        recent_messages=None
    ):

        # Chỉ ghép history khi câu hiện tại
        # thực sự phụ thuộc vào hội thoại trước.
        if not self.needs_conversation_context(
            query=query,
            recent_messages=recent_messages
        ):
            return query


        history_parts = []


        for message in recent_messages[-3:]:

            content = (
                message.content
                or ""
            )

            content = " ".join(
                content.split()
            )


            # History chỉ để resolve reference,
            # không cần nhét quá nhiều text vào embedding.
            if len(content) > 500:

                content = (
                    content[:500]
                    + "..."
                )


            history_parts.append(
                f"{message.role}: "
                f"{content}"
            )


        if not history_parts:
            return query


        history = "\n".join(
            history_parts
        )


        contextual_query = f"""
Current follow-up question:
{query}

Recent conversation is included only to resolve
references in the current question, such as
"nó", "cái đó", "phần trên", "loại thứ 3":

{history}

Retrieve document passages that directly answer
the current follow-up question after resolving
those references.

Current follow-up question:
{query}
"""


        return contextual_query.strip()


    # =====================================================
    # SEARCH
    # =====================================================

    async def search(
        self,
        session_id,
        query,
        recent_messages=None,
        top_k=5,
        candidate_k=10
    ):

        # =================================================
        # 1. CONTEXTUALIZE QUERY ONLY WHEN NEEDED
        # =================================================

        retrieval_query = (
            self.build_contextual_query(
                query=query,
                recent_messages=
                    recent_messages
            )
        )


        # =================================================
        # 2. EMBED QUERY
        # =================================================

        query_embedding = (
            await asyncio.to_thread(
                self.embedder.embed_query,
                retrieval_query
            )
        )


        query_vector = (
            query_embedding.tolist()
        )


        # =================================================
        # 3. PGVECTOR DISTANCE
        # =================================================

        distance = (
            Chunk.embedding
            .cosine_distance(
                query_vector
            )
            .label("distance")
        )


        # =================================================
        # 4. SEARCH DOCUMENTS OF CURRENT SESSION
        # =================================================

        statement = (
            select(
                Chunk,
                Document,
                distance
            )

            .join(
                Document,
                Document.id
                == Chunk.doc_id
            )

            .join(
                ChatSessionDocument,
                ChatSessionDocument.document_id
                == Document.id
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
                distance
            )

            .limit(
                candidate_k
            )
        )


        # =================================================
        # 5. EXECUTE
        # =================================================

        async with (
            async_session_factory()
            as db
        ):

            result = await db.execute(
                statement
            )

            rows = result.all()


        if not rows:
            return []


        # =================================================
        # 6. BUILD DENSE CANDIDATES
        # =================================================

        candidates = []


        for (
            chunk,
            document,
            cosine_distance
        ) in rows:

            cosine_distance = float(
                cosine_distance
            )


            retrieval_score = (
                1.0
                - cosine_distance
            )


            candidates.append({

                "chunk_id":
                    str(chunk.id),

                "document_id":
                    str(document.id),

                "document_name":
                    document.name,

                "page":
                    chunk.page,

                "text":
                    chunk.text,

                "distance":
                    cosine_distance,

                "retrieval_score":
                    retrieval_score
            })


        # =================================================
        # 6b. HYBRID: BM25 + RRF (cấu hình thắng E7)
        # =================================================
        # dense top-K ở trên chỉ là một chân. Chân thứ hai:
        # BM25 trên toàn bộ chunk của session, hợp nhất hai
        # danh sách bằng RRF (k=60) thành pool candidate_k
        # rồi mới rerank ở bước 7 — đúng pipeline đã đo ở
        # E1/E7. RETRIEVAL_MODE=dense giữ hành vi cũ.

        if config.RETRIEVAL_MODE == "hybrid":

            candidates = (
                await self._hybrid_fuse(
                    session_id=
                        session_id,

                    query=
                        retrieval_query,

                    dense_candidates=
                        candidates,

                    candidate_k=
                        candidate_k
                )
            )


        # =================================================
        # 7. RERANK
        # =================================================

        texts = [

            candidate["text"]

            for candidate
            in candidates
        ]


        reranked = (
            await asyncio.to_thread(
                self.reranker.rerank,

                # Independent question:
                # retrieval_query == query.
                #
                # Follow-up:
                # retrieval_query includes only the
                # recent context needed to resolve refs.
                query=
                    retrieval_query,

                documents=
                    texts,

                top_k=
                    top_k
            )
        )


        # =================================================
        # 8. FINAL RESULTS
        # =================================================

        results = []


        for (
            candidate_index,
            rerank_score
        ) in reranked:

            candidate = (
                candidates[
                    candidate_index
                ].copy()
            )


            candidate[
                "rerank_score"
            ] = rerank_score


            results.append(
                candidate
            )


        return results


    # =====================================================
    # HYBRID FUSION (dense + BM25 -> RRF pool)
    # =====================================================

    async def _hybrid_fuse(
        self,
        session_id,
        query,
        dense_candidates,
        candidate_k
    ):

        # ---------------------------------------------
        # 1. UNIVERSE: mọi chunk của session
        # ---------------------------------------------

        statement = (
            select(
                Chunk,
                Document
            )

            .join(
                Document,
                Document.id
                == Chunk.doc_id
            )

            .join(
                ChatSessionDocument,
                ChatSessionDocument.document_id
                == Document.id
            )

            .where(
                ChatSessionDocument.session_id
                == session_id
            )

            .where(
                Document.status
                == "ready"
            )
        )


        async with (
            async_session_factory()
            as db
        ):

            result = await db.execute(
                statement
            )

            rows = result.all()


        if not rows:
            return dense_candidates


        universe = []

        for chunk, document in rows:

            universe.append({

                "chunk_id":
                    str(chunk.id),

                "document_id":
                    str(document.id),

                "document_name":
                    document.name,

                "page":
                    chunk.page,

                "text":
                    chunk.text,

                "distance":
                    None,

                "retrieval_score":
                    0.0
            })


        # ---------------------------------------------
        # 2. BM25 INDEX (cache theo session)
        # ---------------------------------------------

        cached = self._bm25_cache.get(
            session_id
        )

        if (
            cached is None
            or cached[0] != len(universe)
        ):

            index = await asyncio.to_thread(
                BM25Index,

                [
                    item["text"]
                    for item in universe
                ],

                k1=config.BM25_K1,
                b=config.BM25_B
            )

            self._bm25_cache[session_id] = (
                len(universe),
                index
            )

        else:

            index = cached[1]


        bm25_ranked = await asyncio.to_thread(
            index.top_k,
            query,
            candidate_k
        )


        # ---------------------------------------------
        # 3. RRF FUSION TRÊN VỊ TRÍ TRONG UNIVERSE
        # ---------------------------------------------

        position = {
            item["chunk_id"]: i
            for i, item in enumerate(universe)
        }


        dense_positions = [
            position[c["chunk_id"]]
            for c in dense_candidates
            if c["chunk_id"] in position
        ]


        bm25_positions = [
            idx for idx, _ in bm25_ranked
        ]


        fused_positions = rrf_fuse(
            [dense_positions, bm25_positions],
            k=config.RRF_K,
            top_n=candidate_k
        )


        dense_by_id = {
            c["chunk_id"]: c
            for c in dense_candidates
        }


        fused = []

        for rank, pos in enumerate(
            fused_positions,
            start=1
        ):

            item = universe[pos].copy()

            dense_hit = dense_by_id.get(
                item["chunk_id"]
            )

            if dense_hit is not None:

                item["distance"] = (
                    dense_hit["distance"]
                )

            item["retrieval_score"] = (
                1.0 / (config.RRF_K + rank)
            )

            fused.append(item)


        return fused
