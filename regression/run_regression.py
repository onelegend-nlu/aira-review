#!/usr/bin/env python3
"""AIRA regression gate — chạy trước mọi lần build/deploy.

1) Pin cấu hình: mọi giá trị hiệu lực trong src/config.py phải khớp
   cấu hình thắng E7 đã chốt. Lệch một giá trị = FAIL (exit 1).
2) Unit tests: chạy toàn bộ tests/ bằng unittest discover.
   Có test fail/error = FAIL (exit 1). Test bị skip vì thiếu
   tokenizer/model trong môi trường chạy sẽ được in rõ, không
   tính là pass đầy đủ — xem dòng tổng kết cuối.

Cách chạy (trong thư mục gốc project):
    python regression/run_regression.py
"""

import io
import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

WINNER = {
    "CHUNK_MODE": "token",
    "CHUNK_SIZE_TOKENS": 512,
    "CHUNK_OVERLAP_TOKENS": 51,
    "RETRIEVAL_MODE": "hybrid",
    "BM25_K1": 1.5,
    "BM25_B": 0.75,
    "RRF_K": 60,
    "CANDIDATE_K": 40,
    "TOP_K": 5,
}


def check_config() -> bool:
    from src import config

    ok = True
    print("== PIN CẤU HÌNH WINNER E7 ==")
    for name, expected in WINNER.items():
        actual = getattr(config, name, None)
        mark = "OK " if actual == expected else "SAI"
        if actual != expected:
            ok = False
        print(f"[{mark}] {name} = {actual!r} (chốt: {expected!r})")
    print(f"Kết quả pin: {'9/9 khớp' if ok else 'CÓ LỆCH — DỪNG'}")
    return ok


def run_tests() -> tuple[bool, int]:
    print("\n== UNIT TESTS ==")
    loader = unittest.TestLoader()
    suite = loader.discover("tests")
    stream = io.StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=1)
    result = runner.run(suite)
    sys.stdout.write(stream.getvalue())
    skipped = len(result.skipped)
    ok = result.wasSuccessful()
    print(
        f"Tests: {result.testsRun} chạy, "
        f"{len(result.failures)} fail, {len(result.errors)} error, "
        f"{skipped} skipped"
    )
    return ok, skipped


def main() -> int:
    config_ok = check_config()
    tests_ok, skipped = run_tests()
    print("\n== TỔNG KẾT ==")
    if config_ok and tests_ok and skipped == 0:
        print("REGRESSION: PASS (đầy đủ)")
        return 0
    if config_ok and tests_ok and skipped > 0:
        print(
            "REGRESSION: PASS CÓ ĐIỀU KIỆN — "
            f"{skipped} test bị skip trong môi trường này "
            "(thiếu tokenizer/model); phải chạy lại ở môi trường đầy đủ."
        )
        return 0
    print("REGRESSION: FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
