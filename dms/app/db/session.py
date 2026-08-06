from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

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
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- Licensing DB ---
import os

LICENSING_DATABASE_URL = os.environ.get(
    "LICENSING_DATABASE_URL",
    "postgresql+psycopg://dms_user:psqladminpass@127.0.0.1:5432/licensing_db",
)

licensing_engine = create_engine(LICENSING_DATABASE_URL, echo=False, future=True, pool_pre_ping=True)

LicensingSessionLocal = sessionmaker(
    bind=licensing_engine,
    autocommit=False,
    autoflush=False,
)

def get_licensing_db():
    db: Session = LicensingSessionLocal()
    try:
        yield db
    finally:
        db.close()