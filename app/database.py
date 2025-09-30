from contextlib import contextmanager
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DEFAULT_DB_PATH = Path("ipam.db")


def _resolve_database_url() -> str:
    db_path = os.getenv("IPAM_DB_PATH")
    if not db_path:
        return f"sqlite:///{DEFAULT_DB_PATH.resolve()}"

    resolved = Path(db_path)
    if not resolved.is_absolute():
        resolved = Path.cwd() / resolved

    resolved.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{resolved}"


DATABASE_URL = _resolve_database_url()

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
