"""BM25 (Okapi) + RRF — port nguyên bản từ bộ công cụ thí nghiệm
(tools/bm25.py của harness E1–E7) để retrieval trong app dùng ĐÚNG
thuật toán đã được đo kiểm: tokenize lowercase + regex từ Unicode
(âm tiết tiếng Việt giữ thành token riêng), IDF kiểu Lucene
ln(1 + (N - df + .5)/(df + .5)), hợp nhất RRF k=60.
"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class BM25Index:
    def __init__(self, texts: list[str], *, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.n = len(texts)
        self.doc_len: list[int] = []
        self.postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
        df: Counter = Counter()
        for idx, text in enumerate(texts):
            toks = tokenize(text)
            self.doc_len.append(len(toks))
            counts = Counter(toks)
            for term, tf in counts.items():
                self.postings[term].append((idx, tf))
                df[term] += 1
        self.avgdl = (sum(self.doc_len) / self.n) if self.n else 0.0
        self.idf = {
            term: math.log(1.0 + (self.n - d + 0.5) / (d + 0.5))
            for term, d in df.items()
        }

    def top_k(self, query: str, k: int) -> list[tuple[int, float]]:
        scores: dict[int, float] = defaultdict(float)
        q_terms = Counter(tokenize(query))
        for term, q_tf in q_terms.items():
            posts = self.postings.get(term)
            if not posts:
                continue
            idf = self.idf[term]
            for doc_idx, tf in posts:
                dl = self.doc_len[doc_idx]
                denom = tf + self.k1 * (1.0 - self.b + self.b * dl / self.avgdl)
                scores[doc_idx] += idf * (tf * (self.k1 + 1.0) / denom) * (
                    1.0 if q_tf == 1 else (self.k1 + 1.0) * q_tf / (self.k1 + q_tf)
                )
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        return ranked[:k]


def rrf_fuse(rankings: list[list[int]], *, k: int = 60, top_n: int = 40) -> list[int]:
    """Reciprocal Rank Fusion (Cormack et al., SIGIR 2009)."""
    scores: dict[int, float] = defaultdict(float)
    for ranking in rankings:
        for rank, doc_idx in enumerate(ranking, start=1):
            scores[doc_idx] += 1.0 / (k + rank)
    fused = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    return [doc_idx for doc_idx, _ in fused[:top_n]]
