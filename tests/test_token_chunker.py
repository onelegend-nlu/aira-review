"""Unit tests cho chunker token 512/51 (cần tokenizer e5-small;
tự skip nếu transformers/tokenizer chưa sẵn sàng)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from src.chunker import _get_tokenizer, chunk_pages_token

    _TOK = _get_tokenizer()
except Exception:
    _TOK = None


@unittest.skipIf(_TOK is None, "tokenizer e5-small chưa sẵn sàng")
class TestTokenChunker(unittest.TestCase):
    def test_windows_respect_size_and_pages(self):
        text = " ".join(f"từ{i}" for i in range(2000))
        pages = [
            {"page": 1, "text": text},
            {"page": 2, "text": "trang hai ngắn"},
        ]
        chunks = chunk_pages_token(pages, size_tokens=512, overlap_tokens=51)
        self.assertTrue(chunks)
        for c in chunks:
            n = len(_TOK(c["text"], add_special_tokens=False)["input_ids"])
            self.assertLessEqual(n, 512)
        self.assertEqual(chunks[-1]["page"], 2)

    def test_overlap_shares_tokens(self):
        # "từ" là đúng 1 token trong e5 tokenizer: 700 token ->
        # cửa sổ tại 0 và 461 (step = 512 - 51) -> đúng 2 chunk.
        text = " ".join(["từ"] * 700)
        chunks = chunk_pages_token(
            [{"page": 1, "text": text}], size_tokens=512, overlap_tokens=51
        )
        self.assertEqual(len(chunks), 2)
        first = set(_TOK(chunks[0]["text"], add_special_tokens=False)["input_ids"])
        second = _TOK(chunks[1]["text"], add_special_tokens=False)["input_ids"]
        self.assertTrue(first.intersection(second))

    def test_invalid_overlap_rejected(self):
        with self.assertRaises(ValueError):
            chunk_pages_token(
                [{"page": 1, "text": "abc"}], size_tokens=100, overlap_tokens=100
            )


if __name__ == "__main__":
    unittest.main()
