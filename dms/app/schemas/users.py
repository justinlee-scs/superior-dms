from uuid import UUID
from pydantic import BaseModel


class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: str


class UserResponse(BaseModel):
    id: UUID
    username: str
    email: str
    role: str

    class Config:
        from_attributes = True
