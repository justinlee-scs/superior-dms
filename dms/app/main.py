from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.documents import router as documents_router

import app.db.models

app = FastAPI(title="DMS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents_router, prefix="/api")

@app.get("/health")
def health():
    return {"status": "ok"}

allow_origins=["http://localhost:5173"]

from app.db.session import Base, engine

@app.on_event("startup")
def create_tables():
    Base.metadata.create_all(bind=engine)
