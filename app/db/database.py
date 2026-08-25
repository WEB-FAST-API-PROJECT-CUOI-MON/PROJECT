"""Khởi tạo kết nối database (engine, session)."""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy_utils import create_database, database_exists

from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)

Base = declarative_base()

if not database_exists(engine.url):
    create_database(engine.url)


def get_db():
    """Dependency cung cấp một DB session cho mỗi request, tự đóng khi xong."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
