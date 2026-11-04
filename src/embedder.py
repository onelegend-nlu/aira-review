import threading

from sentence_transformers import SentenceTransformer


class Embedder:
    def __init__(self):
        print("Loading embedding model...")

        self.model = SentenceTransformer(
            "intfloat/multilingual-e5-small"
        )

        # SentenceTransformer.encode không an toàn khi nhiều
        # thread gọi đồng thời; khóa lại để dùng với to_thread.
        self._lock = threading.Lock()

        print("Embedding model loaded!")


    def embed_passages(self, texts):
        """
        Tạo embedding cho các chunk tài liệu.
        """

        prepared_texts = [
            "passage: " + text
            for text in texts
        ]

        with self._lock:
            embeddings = self.model.encode(
                prepared_texts,
                batch_size=32,
                normalize_embeddings=True,
                show_progress_bar=True
            )

        return embeddings


    def embed_query(self, query):
        """
        Tạo embedding cho câu hỏi.
        """

        with self._lock:
            embedding = self.model.encode(
                [
                    "query: " + query
                ],
                normalize_embeddings=True
            )[0]

        return embedding
