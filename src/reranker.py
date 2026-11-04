import threading

from sentence_transformers import CrossEncoder


class Reranker:
    def __init__(self):
        print("Loading reranker model...")

        self.model = CrossEncoder(
            "BAAI/bge-reranker-base"
        )

        # CrossEncoder.predict không an toàn khi nhiều thread
        # gọi đồng thời; khóa lại để dùng với to_thread.
        self._lock = threading.Lock()

        print("Reranker loaded!")


    def rerank(
        self,
        query,
        documents,
        top_k=5
    ):
        if not documents:
            return []

        pairs = [
            [query, document]
            for document in documents
        ]

        with self._lock:
            scores = self.model.predict(
                pairs
            )

        ranked = sorted(
            enumerate(scores),
            key=lambda item: item[1],
            reverse=True
        )

        return [
            (
                original_index,
                float(score)
            )
            for original_index, score
            in ranked[:top_k]
        ]
