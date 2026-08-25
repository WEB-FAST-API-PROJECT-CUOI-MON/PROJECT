"""Exception handler dùng chung: chuẩn hoá format lỗi JSON trả về cho client.

Mọi lỗi (404/400/403/401, lỗi validate dữ liệu, lỗi hệ thống không lường trước)
đều được trả về theo cùng một cấu trúc:

    {"error": {"status_code": <int>, "message": <str>, "details": <optional>}}
"""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def _error_response(status_code: int, message: str, details=None) -> JSONResponse:
    """Dựng JSONResponse lỗi theo format thống nhất."""
    body: dict = {"error": {"status_code": status_code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=body)


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Chuẩn hoá lỗi cho các HTTPException chủ động raise trong router (404/400/403/401,...)."""
    return _error_response(exc.status_code, str(exc.detail))


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Chuẩn hoá lỗi khi dữ liệu request không hợp lệ (422)."""
    return _error_response(
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "Dữ liệu đầu vào không hợp lệ",
        details=exc.errors(),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Bắt các lỗi không lường trước (500), tránh lộ traceback cho client."""
    return _error_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR, "Lỗi hệ thống, vui lòng thử lại sau"
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Đăng ký toàn bộ exception handler cho app FastAPI."""
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
