"""Test bộ đếm rate limit (src/rate_limit.py).

Dùng đồng hồ giả tiêm vào RateLimiter để kiểm tra cửa sổ
trượt mà không phải chờ thời gian thật.
"""

import unittest

from src.rate_limit import RateLimiter


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class RateLimiterTest(unittest.TestCase):

    def test_under_limit_allowed(self):
        clock = FakeClock()
        limiter = RateLimiter(3, clock=clock)

        self.assertTrue(limiter.allow("1.2.3.4"))
        self.assertTrue(limiter.allow("1.2.3.4"))
        self.assertTrue(limiter.allow("1.2.3.4"))

    def test_over_limit_rejected(self):
        clock = FakeClock()
        limiter = RateLimiter(3, clock=clock)

        for _ in range(3):
            self.assertTrue(limiter.allow("1.2.3.4"))

        self.assertFalse(limiter.allow("1.2.3.4"))
        self.assertFalse(limiter.allow("1.2.3.4"))

    def test_window_slides_and_frees_slots(self):
        clock = FakeClock()
        limiter = RateLimiter(
            2,
            window_seconds=60.0,
            clock=clock,
        )

        self.assertTrue(limiter.allow("ip"))
        clock.advance(30)
        self.assertTrue(limiter.allow("ip"))
        self.assertFalse(limiter.allow("ip"))

        # Sau 31s nữa, request đầu tiên (t=0) rời cửa sổ,
        # request thứ hai (t=30) vẫn còn trong cửa sổ.
        clock.advance(31)
        self.assertTrue(limiter.allow("ip"))
        self.assertFalse(limiter.allow("ip"))

    def test_rejected_request_not_counted(self):
        clock = FakeClock()
        limiter = RateLimiter(
            1,
            window_seconds=60.0,
            clock=clock,
        )

        self.assertTrue(limiter.allow("ip"))
        clock.advance(50)
        self.assertFalse(limiter.allow("ip"))

        # Request bị từ chối ở t=50 không được ghi nhận:
        # tới t=61 cửa sổ chỉ còn tính từ t>1 nên trống.
        clock.advance(11)
        self.assertTrue(limiter.allow("ip"))

    def test_keys_are_independent(self):
        clock = FakeClock()
        limiter = RateLimiter(1, clock=clock)

        self.assertTrue(limiter.allow("10.0.0.1"))
        self.assertFalse(limiter.allow("10.0.0.1"))
        self.assertTrue(limiter.allow("10.0.0.2"))

    def test_zero_limit_disables(self):
        clock = FakeClock()
        limiter = RateLimiter(0, clock=clock)

        for _ in range(100):
            self.assertTrue(limiter.allow("ip"))

    def test_remaining_and_reset(self):
        clock = FakeClock()
        limiter = RateLimiter(2, clock=clock)

        self.assertEqual(limiter.remaining("ip"), 2)
        limiter.allow("ip")
        self.assertEqual(limiter.remaining("ip"), 1)

        limiter.reset("ip")
        self.assertEqual(limiter.remaining("ip"), 2)


if __name__ == "__main__":
    unittest.main()
