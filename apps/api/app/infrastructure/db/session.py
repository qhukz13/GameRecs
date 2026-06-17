from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# Normalize DATABASE_URL to use psycopg v3 dialect.
# Render (and many cloud providers) return URLs like 'postgresql://...' or 'postgres://...'
# which SQLAlchemy maps to psycopg2 by default. We force psycopg v3 here.
def _normalize_db_url(url: str) -> str:
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url  # already has a dialect specified (e.g. postgresql+psycopg://...)

engine = create_engine(_normalize_db_url(settings.database_url), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

