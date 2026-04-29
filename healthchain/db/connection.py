import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

from healthchain.config.appconfig import AppConfig
from healthchain.db.models.audit import Base

config = AppConfig.load()
DATABASE_URL = (
    config.compliance.audit.database_url
    if config and config.compliance.audit.database_url
    else "sqlite:///./healthchain.db"
)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def session_scope():
    """
    Provide a transactional scope around a series of operations.
    This ensures that the session is always closed, even if an error occurs.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()