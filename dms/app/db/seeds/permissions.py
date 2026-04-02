from sqlalchemy.orm import Session
from app.db.models.permission import Permission
from app.services.rbac.policy import Permissions

ALL_PERMISSIONS = [
    Permissions.DOCUMENT_READ,
    Permissions.DOCUMENT_UPLOAD,
    Permissions.DOCUMENT_DELETE,
    Permissions.DOCUMENT_DOWNLOAD,
    Permissions.DOCUMENT_PREVIEW,
    Permissions.DOCUMENT_MOVE,
    Permissions.DOCUMENT_UPDATE,
    Permissions.DOCUMENT_VERSION_READ,
    Permissions.DOCUMENT_VERSION_CREATE,
    Permissions.DOCUMENT_VERSION_PREVIEW,
    Permissions.DOCUMENT_VERSION_DOWNLOAD,
    Permissions.DOCUMENT_VERSION_SET_CURRENT,
    Permissions.DOCUMENT_TAG_READ,
    Permissions.DOCUMENT_TAG_EDIT,
    Permissions.DOCUMENT_DUE_PAYMENTS,
    Permissions.WORKFLOW_ASSIGN,
    Permissions.WORKFLOW_ADVANCE,
    Permissions.ADMIN_USERS,
    Permissions.ADMIN_ROLES,
]


def seed_permissions(db: Session):
    """Seed permissions.

    Parameters:
        db (type=Session): Database session used for persistence operations.
    """
    for key in ALL_PERMISSIONS:
        exists = db.query(Permission).filter_by(key=key).first()
        if not exists:
            db.add(Permission(key=key, description=key))
    db.commit()
