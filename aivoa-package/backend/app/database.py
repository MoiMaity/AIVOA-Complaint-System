"""Database engine and session management.

Works with either Postgres or MySQL — the driver is chosen entirely by the
DATABASE_URL in .env, so no code changes are needed to switch.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # drops dead connections instead of raising mid-request
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: one session per request, always closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables if they don't exist.

    Fine for this assessment. A production QMS would use Alembic migrations,
    because regulated systems need an auditable schema history.
    """
    from app import models  # noqa: F401  (import registers the models)

    Base.metadata.create_all(bind=engine)
