from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.db.models
from app.db.base import Base
from app.core.config import settings

DATABASE_URL = settings.database_url

engine = create_engine(DATABASE_URL, echo=False, future=True, pool_pre_ping=True)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

def get_db():
    """Return db.

    Parameters:
        None.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
