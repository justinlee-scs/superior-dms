from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.documents import router as documents_router
from app.api.v1.rbac import api_router as rbac_router
from app.api.auth import router as auth_router

import app.db.models

from fastapi import Depends
from app.auth.deps import get_current_user
from app.db.models.user import User

app = FastAPI(title="DMS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents_router)
app.include_router(auth_router)
app.include_router(rbac_router, prefix="/rbac")

@app.get("/")
def root():
    return {"message": "DMS API running"}

@app.get("/documents")
def list_docs(user: User = Depends(get_current_user)):
    return {"msg": f"Hello {user.email}"}

@app.get("/health")
def health():
    return {"status": "ok"}

from app.db.session import Base, engine

@app.on_event("startup")
def create_tables():
    Base.metadata.create_all(bind=engine)
    # Lightweight compatibility migration for older local DBs.
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                ALTER TABLE document_versions
                ADD COLUMN IF NOT EXISTS tags JSON NOT NULL DEFAULT '[]'::json
                """
            )
        )
        conn.execute(
            text(
                """
                ALTER TABLE document_versions
                ADD COLUMN IF NOT EXISTS ocr_raw_confidence DOUBLE PRECISION
                """
            )
        )
        conn.execute(
            text(
                """
                ALTER TABLE document_versions
                ADD COLUMN IF NOT EXISTS ocr_engine VARCHAR(64)
                """
            )
        )
        conn.execute(
            text(
                """
                ALTER TABLE document_versions
                ADD COLUMN IF NOT EXISTS ocr_model_version VARCHAR(128)
                """
            )
        )
        conn.execute(
            text(
                """
                ALTER TABLE document_versions
                ADD COLUMN IF NOT EXISTS ocr_latency_ms INTEGER
                """
            )
        )
