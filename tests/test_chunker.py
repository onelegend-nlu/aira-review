"""Test cho chunker mới (chỉ dùng stdlib, chạy: python -m unittest discover -s tests)."""

import inspect
import unittest

from src.chunker import chunk_pages


class ChunkerTest(unittest.TestCase):

    def test_defaults_match_production(self):
        params = inspect.signature(chunk_pages).parameters
        self.assertEqual(params["chunk_size"].default, 100)
        self.assertEqual(params["overlap"].default, 20)

    def test_no_mid_sentence_split(self):
        text = (
            "Học máy là một lĩnh vực của trí tuệ nhân tạo. "
            "Nó cho phép máy học từ dữ liệu! "
            "Bạn đã hiểu chưa? "
            "Chúng ta sẽ học tiếp ở chương sau."
        )
        chunks = chunk_pages(
            [{"page": 1, "text": text}],
            chunk_size=12,
            overlap=4,
        )
        self.assertGreaterEqual(len(chunks), 2)
        for chunk in chunks:
            self.assertTrue(
                chunk["text"].rstrip().endswith((".", "!", "?")),
                f"chunk cắt giữa câu: {chunk['text']!r}",
            )

    def test_sentence_overlap_carried(self):
        text = "Câu một ở đây. Câu hai ở đây. Câu ba ở đây. Câu bốn ở đây."
        chunks = chunk_pages(
            [{"page": 1, "text": text}],
            chunk_size=8,
            overlap=4,
        )
        self.assertGreaterEqual(len(chunks), 2)
        # chunk sau mở đầu bằng câu cuối của chunk trước
        self.assertTrue(
            chunks[1]["text"].startswith("Câu hai")
            or chunks[1]["text"].startswith("Câu ba")
        )

    def test_long_segment_falls_back_to_word_window(self):
        text = " ".join(["từ"] * 250)
        chunks = chunk_pages(
            [{"page": 3, "text": text}],
            chunk_size=100,
            overlap=20,
        )
        self.assertEqual(len(chunks), 3)
        self.assertTrue(
            all(len(c["text"].split()) <= 100 for c in chunks)
        )
        self.assertTrue(all(c["page"] == 3 for c in chunks))

    def test_ids_sequential_and_empty_pages_skipped(self):
        pages = [
            {"page": 1, "text": "   "},
            {"page": 2, "text": "Một câu duy nhất."},
        ]
        chunks = chunk_pages(pages, chunk_size=100, overlap=20)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["chunk_id"], 0)
        self.assertEqual(chunks[0]["page"], 2)

    def test_invalid_overlap_rejected(self):
        with self.assertRaises(ValueError):
            chunk_pages(
                [{"page": 1, "text": "abc def"}],
                chunk_size=10,
                overlap=10,
            )


if __name__ == "__main__":
    unittest.main()
