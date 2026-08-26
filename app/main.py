"""File gốc khởi chạy FastAPI."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.exceptions import register_exception_handlers
from app.core.response_envelope import StandardResponseMiddleware
from app.db.database import Base, SessionLocal, engine
from app.models import activity_log, site, team, user, work_item  # noqa: F401 - import để đăng ký model với Base
from app.routers import auth, site as site_router, team as team_router, users, work_item as work_item_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Construction Management API")

register_exception_handlers(app)
app.add_middleware(StandardResponseMiddleware)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(site_router.router)
app.include_router(team_router.router)
app.include_router(work_item_router.router)


@app.get("/", tags=["Health"], summary="Kiểm tra API đang chạy")
def root():
    """Endpoint gốc, dùng để xác nhận nhanh API đã khởi động (không kiểm tra database)."""
    return {"message": "Construction Management API đang chạy"}


@app.get("/health", tags=["Health"], summary="Health check")
def health_check():
    """Kiểm tra API và kết nối database còn hoạt động (dùng cho monitoring/uptime check)."""
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
        finally:
            db.close()
        return {"status": "ok", "database": "ok"}
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "database": "unreachable"},
        )
