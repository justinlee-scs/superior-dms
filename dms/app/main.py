from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.documents import router as documents_router
from app.api.v1.rbac import api_router as rbac_router
from app.api.auth import router as auth_router
from app.api.processing import router as processing_router
from app.api.labelstudio_ml import router as labelstudio_router
from app.api.admin_training import router as admin_training_router

import app.db.models

from fastapi import Depends
from app.auth.deps import get_current_user
from app.db.models.user import User
from app.core.config import settings
from app.services.nightly_retrainer import start_nightly_retrainer

app = FastAPI(title="DMS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents_router)
app.include_router(auth_router)
app.include_router(processing_router)
app.include_router(rbac_router, prefix="/rbac")
app.include_router(labelstudio_router)
app.include_router(admin_training_router)


@app.on_event("startup")
def _startup_jobs() -> None:
    start_nightly_retrainer()

@app.get("/")
def root():
    """Handle root.

    Parameters:
        None.
    """
    return {"message": "DMS API running"}

@app.get("/documents")
def list_docs(user: User = Depends(get_current_user)):
    """Return docs.

    Parameters:
        user (type=User, default=Depends(get_current_user)): Authenticated user context for authorization and ownership checks.
    """
    return {"msg": f"Hello {user.email}"}

@app.get("/health")
def health():
    """Handle health.

    Parameters:
        None.
    """
    return {"status": "ok"}
