from sqlalchemy.orm import Session
from app.db.models.permission import Permission
from app.services.rbac.policy import Permissions

ALL_PERMISSIONS = [
    Permissions.DOCUMENT_READ,
    Permissions.DOCUMENT_UPLOAD,
    Permissions.DOCUMENT_DELETE,
    Permissions.WORKFLOW_ASSIGN,
    Permissions.WORKFLOW_ADVANCE,
    Permissions.ADMIN_USERS,
    Permissions.ADMIN_ROLES,
]


def seed_permissions(db: Session):
    for key in ALL_PERMISSIONS:
        exists = db.query(Permission).filter_by(key=key).first()
        if not exists:
            db.add(Permission(key=key, description=key))
    db.commit()
