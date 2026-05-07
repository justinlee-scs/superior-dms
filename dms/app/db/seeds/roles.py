from sqlalchemy.orm import Session
from app.db.models.role import Role
from app.db.models.permission import Permission


# NEED TO REFACTOR TO DO USER/ROLE EDITING AND WORKFLOW STATUS UPDATING

ROLE_PERMISSION_MAP = {
    "admin": "ALL",
    "unassigned": [
        "user.password_set_self",
    ],
    "editor": [
        "document.read",
        "document.upload",
        "document.download",
        "document.preview",
        "document.move",
        "document.project_move",
        "document.update",
        "document_version.read",
        "document_version.create",
        "document_version.preview",
        "document_version.download",
        "document_version.set_current",
        "tags.read",
        "tags.edit",
        "document.due_payments",
        "user.password_set_self",
    ],
    "viewer": [
        "document.read",
        "document.download",
        "document.preview",
        "document_version.read",
        "document_version.preview",
        "document_version.download",
        "document.due_payments",
        "user.password_set_self",
    ],
}

def seed_roles(db: Session):

    # Fetch all permissions once
    """Seed roles.

    Parameters:
        db (type=Session): Database session used for persistence operations.
    """
    all_permissions = db.query(Permission).all()
    permission_lookup = {p.key: p for p in all_permissions}

    for role_name, permissions in ROLE_PERMISSION_MAP.items():

        role = db.query(Role).filter_by(name=role_name).first()
        if not role:
            role = Role(name=role_name)
            db.add(role)
            db.flush()

        if permissions == "ALL":
            role.permissions = all_permissions
        else:
            role.permissions = [
                permission_lookup[key]
                for key in permissions
                if key in permission_lookup
            ]

    db.commit()
