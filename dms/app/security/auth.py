from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.user import User


def get_current_user(db: Session = Depends(get_db)) -> User:
    """TEMPORARY AUTH STUB.

    Parameters:
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
    """
    user = db.query(User).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No users exist"
        )

    return user
