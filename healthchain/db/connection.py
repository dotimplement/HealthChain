import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from contextlib import contextmanager

# connect to database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./healthchain.db")

# set up the database
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


Base = declarative_base()

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