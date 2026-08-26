"""Exception handler dùng chung: chuẩn hoá format lỗi JSON trả về cho client.

Mọi response API (thành công lẫn lỗi) đều theo cùng 6 trường chuẩn — xem
`app.core.response_envelope`. Response lỗi được dựng đúng format ngay tại đây; response
thành công được `StandardResponseMiddleware` bọc lại ở tầng transport.
"""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.response_envelope import build_envelope


def _error_response(request: Request, status_code: int, message: str, details=None) -> JSONResponse:
    """Dựng JSONResponse lỗi theo đúng 6 trường chuẩn (statusCode/message/data/error/path/timestamp)."""
    body = build_envelope(
        status_code=status_code,
        message=message,
        path=request.url.path,
        data=None,
        error=details if details is not None else message,
    )
    return JSONResponse(status_code=status_code, content=body)


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Chuẩn hoá lỗi cho các HTTPException chủ động raise trong router (404/400/403/401,...)."""
    return _error_response(request, exc.status_code, str(exc.detail))


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Chuẩn hoá lỗi khi dữ liệu request không hợp lệ (422)."""
    return _error_response(
        request,
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "Dữ liệu đầu vào không hợp lệ",
        details=exc.errors(),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Bắt các lỗi không lường trước (500), tránh lộ traceback cho client."""
    return _error_response(
        request, status.HTTP_500_INTERNAL_SERVER_ERROR, "Lỗi hệ thống, vui lòng thử lại sau"
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Đăng ký toàn bộ exception handler cho app FastAPI."""
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
