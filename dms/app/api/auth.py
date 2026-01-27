from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.user import User
from app.auth import verify_password, create_access_token
from app.schemas.auth import TokenResponse

router = APIRouter(tags=["auth"])


@router.post("/token", response_model=TokenResponse)
def login(
    username: str,
    password: str,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token)
