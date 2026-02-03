from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.user import User


def get_current_user(db: Session = Depends(get_db)) -> User:
    # TEMP: replace with real auth later
    return db.query(User).first()
