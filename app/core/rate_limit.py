"""Rate limiter chống brute-force cho /auth/login — mức demo, lưu trạng thái in-memory.

Giới hạn: chỉ đúng khi chạy 1 tiến trình (không chia sẻ giữa nhiều worker/instance).
Muốn dùng thật cho production nên thay bằng Redis hoặc middleware chuyên dụng
(vd. slowapi) để trạng thái được chia sẻ và không mất khi restart.
"""

import time
from collections import defaultdict

from fastapi import HTTPException, Request, status

from app.core.config import settings

_attempts: dict[str, list[float]] = defaultdict(list)


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def check_login_rate_limit(request: Request) -> None:
    """Raise 429 nếu vượt quá số lần gọi login cho phép trong khoảng thời gian cấu hình."""
    key = _client_key(request)
    now = time.time()
    window_start = now - settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS
    attempts = [t for t in _attempts[key] if t > window_start]

    if len(attempts) >= settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS:
        _attempts[key] = attempts
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Bạn đã thử đăng nhập quá nhiều lần, vui lòng thử lại sau ít phút.",
        )

    attempts.append(now)
    _attempts[key] = attempts


def _reset_state_for_tests() -> None:
    """Chỉ dùng trong test: xóa toàn bộ trạng thái rate limit để mỗi test có quota riêng."""
    _attempts.clear()
