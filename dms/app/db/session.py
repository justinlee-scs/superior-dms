import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.db.models
from app.db.base import Base


DEFAULT_DATABASE_URL = "postgresql+psycopg://dms_user:dms_password@localhost:5432/dms"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

engine = create_engine(DATABASE_URL, echo=False, future=True, pool_pre_ping=True)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
