"""Test ánh xạ chế độ tốc độ truy xuất -> pool rerank.

Nguồn duy nhất của ánh xạ là src/config.py
(RETRIEVAL_MODES / DEFAULT_MODE / candidate_k_for_mode).
Ba chế độ chỉ đổi pool đưa vào reranker; chế độ mặc định
"lau" phải luôn cho pool 40 = CANDIDATE_K (winner E7).
"""

import unittest

from src import config


class RetrievalModesTest(unittest.TestCase):

    def test_valid_modes_map_to_expected_pools(self):
        self.assertEqual(
            config.candidate_k_for_mode("lau"),
            40,
        )
        self.assertEqual(
            config.candidate_k_for_mode("trung_binh"),
            20,
        )
        self.assertEqual(
            config.candidate_k_for_mode("nhanh"),
            10,
        )

    def test_modes_dict_has_exactly_the_three_modes(self):
        self.assertEqual(
            config.RETRIEVAL_MODES,
            {
                "lau": 40,
                "trung_binh": 20,
                "nhanh": 10,
            },
        )

    def test_default_mode_is_lau_with_winner_pool(self):
        self.assertEqual(config.DEFAULT_MODE, "lau")
        self.assertEqual(
            config.RETRIEVAL_MODES[config.DEFAULT_MODE],
            config.CANDIDATE_K,
        )
        self.assertEqual(config.CANDIDATE_K, 40)

    def test_missing_mode_uses_default_pool(self):
        self.assertEqual(
            config.candidate_k_for_mode(None),
            40,
        )
        self.assertEqual(
            config.candidate_k_for_mode(""),
            40,
        )

    def test_unknown_mode_uses_default_pool(self):
        self.assertEqual(
            config.candidate_k_for_mode("turbo"),
            40,
        )
        self.assertEqual(
            config.candidate_k_for_mode("LAU"),
            40,
        )


if __name__ == "__main__":
    unittest.main()
