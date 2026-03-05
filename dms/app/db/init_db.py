from app.db.session import engine, Base

# Force model registration
from app.db.models.user import User
from app.db.models.role import Role
from app.db.models.permission import Permission

from app.db.models.user_role import user_roles
from app.db.models.role_permission import role_permissions

from app.db.models.user_permission_override import UserPermissionOverride

from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion


def init_db():
    #print("Registered tables:", list(Base.metadata.tables.keys()))
    """Handle init db.

    Parameters:
        None.
    """
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
