from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import Column

from app.db.base import Base


class RetrainScheduleSetting(Base):
    __tablename__ = "retrain_schedule_settings"

    id = Column(sa.Integer, primary_key=True, default=1)
    enabled = Column(sa.Boolean, nullable=False, default=True)
    timezone = Column(sa.String(64), nullable=False, default="America/Los_Angeles")
    hour = Column(sa.Integer, nullable=False, default=3)
    minute = Column(sa.Integer, nullable=False, default=0)
    updated_at = Column(sa.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
