"""Unit tests cho src/bm25.py (stdlib unittest, không cần model)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.bm25 import BM25Index, rrf_fuse, tokenize


class TestBM25(unittest.TestCase):
    def test_tokenize_vietnamese_syllables(self):
        self.assertEqual(
            tokenize("Mạng máy tính 101"),
            ["mạng", "máy", "tính", "101"],
        )

    def test_rare_term_doc_ranks_first(self):
        texts = [
            "con mèo con chó con gà",
            "giao thức xyzzy định tuyến đặc biệt",
            "con mèo ngủ trên mái nhà",
        ]
        index = BM25Index(texts, k1=1.5, b=0.75)
        top = index.top_k("xyzzy", 3)
        self.assertEqual(top[0][0], 1)

    def test_rrf_fuse_rewards_agreement(self):
        # doc 2: hạng 1 ở danh sách đầu + hạng 2 ở danh sách sau
        # (1/61 + 1/62) -> cao nhất; các doc còn lại chỉ xuất
        # hiện một lần.
        fused = rrf_fuse([[2, 0], [1, 2]], k=60, top_n=3)
        self.assertEqual(fused[0], 2)
        self.assertEqual(sorted(fused), [0, 1, 2])


if __name__ == "__main__":
    unittest.main()
