"""Rate limit nhẹ theo cửa sổ trượt (sliding window).

Thuần thư viện chuẩn — không thêm dependency. Mục đích duy nhất:
chống spam đốt quota Gemini/CPU trên bản demo public (giới hạn số
request chat/upload mỗi IP trong một phút). Không phải cơ chế
bảo mật — IP có thể bị giả mạo qua proxy, và bản đồ đếm nằm trong
RAM của tiến trình nên reset khi backend khởi động lại.

Cách dùng:

    limiter = RateLimiter(limit_per_minute=30)

    if not limiter.allow(client_ip):
        # trả HTTP 429

Đặt limit_per_minute = 0 để tắt hẳn (allow luôn trả True).
Đồng hồ có thể tiêm vào (tham số clock) để test cửa sổ trượt
mà không phải chờ thật.
"""

import threading
import time

from collections import deque


class RateLimiter:
    """Đếm số request theo khóa (IP) trong cửa sổ trượt."""

    def __init__(
        self,
        limit_per_minute: int,
        window_seconds: float = 60.0,
        clock=time.monotonic,
    ):
        self.limit = int(limit_per_minute)
        self.window = float(window_seconds)
        self._clock = clock
        self._lock = threading.Lock()
        self._hits: dict[str, deque] = {}

    def _prune(
        self,
        timestamps: deque,
        now: float,
    ) -> None:
        cutoff = now - self.window

        while timestamps and timestamps[0] <= cutoff:
            timestamps.popleft()

    def allow(
        self,
        key: str,
    ) -> bool:
        """True nếu request được phép (và ghi nhận nó).

        False nếu khóa đã chạm giới hạn trong cửa sổ hiện tại
        (request bị từ chối KHÔNG được ghi nhận thêm).
        """
        if self.limit <= 0:
            return True

        now = self._clock()

        with self._lock:
            timestamps = self._hits.setdefault(
                key,
                deque(),
            )

            self._prune(timestamps, now)

            if len(timestamps) >= self.limit:
                return False

            timestamps.append(now)

            return True

    def remaining(
        self,
        key: str,
    ) -> int:
        """Số request còn lại của khóa trong cửa sổ hiện tại."""
        if self.limit <= 0:
            return self.limit

        now = self._clock()

        with self._lock:
            timestamps = self._hits.get(key)

            if timestamps is None:
                return self.limit

            self._prune(timestamps, now)

            return max(
                0,
                self.limit - len(timestamps),
            )

    def reset(
        self,
        key: str | None = None,
    ) -> None:
        """Xóa bộ đếm của một khóa, hoặc của mọi khóa."""
        with self._lock:
            if key is None:
                self._hits.clear()
            else:
                self._hits.pop(key, None)
