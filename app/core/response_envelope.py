"""Chuẩn hoá format response: MỌI API (thành công lẫn lỗi) đều trả về đúng 6 trường:

    {"statusCode": <int>, "message": <str>, "data": <any|null>,
     "error": <any|null>, "path": <str>, "timestamp": <str ISO-8601>}

Response lỗi được `app.core.exceptions` dựng sẵn đúng 6 trường này (dùng `build_envelope`).
Response thành công (router trả về bình thường, không biết gì về envelope) được
`StandardResponseMiddleware` bên dưới bọc lại ở tầng transport, không cần sửa từng endpoint.
"""

import json
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Path phục vụ tài liệu API (Swagger/OpenAPI) — giữ nguyên định dạng gốc, không bọc lại,
# nếu không Swagger UI / các tool đọc OpenAPI sẽ không parse được.
#
# /auth/login và /auth/refresh cũng phải giữ nguyên: đây là các token endpoint theo
# chuẩn OAuth2 (RFC 6749), client (Swagger UI "Authorize", hoặc bất kỳ OAuth2 client chuẩn
# nào) đọc "access_token" ở top-level response. Nếu bọc vào "data" như các API khác,
# access_token sẽ bị lồng bên trong khiến các client này không lấy được token thật.
_EXCLUDED_PATHS = {
    "/openapi.json",
    "/docs",
    "/docs/oauth2-redirect",
    "/redoc",
    "/auth/login",
    "/auth/refresh",
}

_STANDARD_KEYS = {"statusCode", "message", "data", "error", "path", "timestamp"}

_SUCCESS_MESSAGE_BY_METHOD = {
    "GET": "Lấy dữ liệu thành công",
    "POST": "Tạo mới thành công",
    "PUT": "Cập nhật thành công",
    "PATCH": "Cập nhật thành công",
    "DELETE": "Xóa thành công",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_envelope(status_code: int, message: str, path: str, data=None, error=None) -> dict:
    """Dựng dict theo đúng 6 trường chuẩn — dùng chung cho cả response lỗi (exceptions.py)
    và response thành công (StandardResponseMiddleware)."""
    return {
        "statusCode": status_code,
        "message": message,
        "data": data,
        "error": error,
        "path": path,
        "timestamp": now_iso(),
    }


class StandardResponseMiddleware(BaseHTTPMiddleware):
    """Bọc mọi response JSON thành công vào envelope chuẩn 6 trường.

    Response lỗi (đã được app.core.exceptions chuẩn hoá sẵn đúng envelope) được nhận diện
    qua đúng bộ 6 key và giữ nguyên, tránh bọc lồng hai lớp.
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # 204/304 không được phép có body theo chuẩn HTTP -> không đụng vào.
        if request.url.path in _EXCLUDED_PATHS or response.status_code in (204, 304):
            return response

        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            return response

        body_bytes = b"".join([chunk async for chunk in response.body_iterator])

        if not body_bytes:
            payload = None
        else:
            try:
                payload = json.loads(body_bytes)
            except ValueError:
                # Không phải JSON hợp lệ (không nên xảy ra) -> trả nguyên response gốc.
                return Response(
                    content=body_bytes,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                )

        if isinstance(payload, dict) and set(payload.keys()) == _STANDARD_KEYS:
            envelope = payload  # đã được exceptions.py chuẩn hoá sẵn (lỗi) -> không bọc lại
        elif response.status_code >= 400:
            # Response lỗi được endpoint tự dựng bằng JSONResponse (không raise qua
            # HTTPException, vd. /health khi mất kết nối DB) -> vẫn phải chuẩn hoá đúng
            # envelope lỗi (error != null), không được gắn nhầm message "thành công".
            message = payload.get("message") if isinstance(payload, dict) else None
            envelope = build_envelope(
                status_code=response.status_code,
                message=message if isinstance(message, str) else "Đã xảy ra lỗi",
                path=request.url.path,
                data=None,
                error=payload,
            )
        else:
            message = _SUCCESS_MESSAGE_BY_METHOD.get(request.method, "Thành công")
            envelope = build_envelope(
                status_code=response.status_code, message=message, path=request.url.path, data=payload
            )

        new_body = json.dumps(envelope, ensure_ascii=False).encode("utf-8")
        headers = dict(response.headers)
        headers["content-length"] = str(len(new_body))
        return Response(
            content=new_body, status_code=response.status_code, headers=headers, media_type="application/json"
        )
