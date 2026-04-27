from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.models.retrain_schedule_setting import RetrainScheduleSetting
from app.db.session import get_db
from app.services.nightly_retrainer import reload_nightly_retrainer
from app.services.rbac.permission_checker import require_permission
from app.services.rbac.policy import Permissions

router = APIRouter(prefix="/admin/training", tags=["admin-training"])


class RetrainScheduleResponse(BaseModel):
    enabled: bool
    timezone: str
    hour: int
    minute: int
    updated_at: datetime | None = None


class RetrainScheduleUpdateRequest(BaseModel):
    enabled: bool
    timezone: str = Field(min_length=1, max_length=64)
    hour: int = Field(ge=0, le=23)
    minute: int = Field(ge=0, le=59)


def _get_or_create(db: Session) -> RetrainScheduleSetting:
    row = db.get(RetrainScheduleSetting, 1)
    if row:
        return row
    row = RetrainScheduleSetting(
        id=1,
        enabled=True,
        timezone="America/Los_Angeles",
        hour=3,
        minute=0,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get(
    "/schedule",
    response_model=RetrainScheduleResponse,
    dependencies=[Depends(require_permission(Permissions.ADMIN_TRAINING))],
)
def get_schedule(db: Session = Depends(get_db)) -> RetrainScheduleResponse:
    row = _get_or_create(db)
    return RetrainScheduleResponse(
        enabled=row.enabled,
        timezone=row.timezone,
        hour=row.hour,
        minute=row.minute,
        updated_at=row.updated_at,
    )


@router.put(
    "/schedule",
    response_model=RetrainScheduleResponse,
    dependencies=[Depends(require_permission(Permissions.ADMIN_TRAINING))],
)
def update_schedule(
    payload: RetrainScheduleUpdateRequest,
    db: Session = Depends(get_db),
) -> RetrainScheduleResponse:
    try:
        ZoneInfo(payload.timezone)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid timezone")

    row = _get_or_create(db)
    row.enabled = payload.enabled
    row.timezone = payload.timezone
    row.hour = payload.hour
    row.minute = payload.minute
    db.commit()
    db.refresh(row)

    reload_nightly_retrainer()

    return RetrainScheduleResponse(
        enabled=row.enabled,
        timezone=row.timezone,
        hour=row.hour,
        minute=row.minute,
        updated_at=row.updated_at,
    )
