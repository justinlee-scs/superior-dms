from pathlib import Path
import sys

# Ensure project root is on PYTHONPATH
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

import uuid
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models.user import User
from app.db.models.role import Role
from app.services.rbac.access_resolver import resolve_permissions
from app.auth.jwt import hash_password

# Config
ADMIN_EMAIL = "justin.lee@scsgroup.ca"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "jlscspass"
ADMIN_ROLE_NAME = "admin"

def main():
    db: Session = SessionLocal()

    try:
        # 1️⃣ Ensure role exists
        role = db.query(Role).filter(Role.name == ADMIN_ROLE_NAME).one_or_none()
        if not role:
            role = Role(name=ADMIN_ROLE_NAME)
            db.add(role)
            db.flush()  # ensures role.id exists
            print(f"Created role: {ADMIN_ROLE_NAME}")

        # 2️⃣ Ensure user exists
        user = db.query(User).filter(User.email == ADMIN_EMAIL).one_or_none()
        if not user:
            user = User(
                id=uuid.uuid4(),
                username=ADMIN_USERNAME,
                email=ADMIN_EMAIL,
                hashed_password=hash_password(ADMIN_PASSWORD),
                is_active=True,
            )
            db.add(user)
            db.flush()
            print(f"Created user: {ADMIN_EMAIL}")

        # 3️⃣ Ensure user has the role
        if role not in user.roles:
            user.roles.append(role)
            print(f"Assigned role '{ADMIN_ROLE_NAME}' to user '{ADMIN_EMAIL}'")

        db.commit()

        # 4️⃣ Print effective permissions
        perms = resolve_permissions(db, user)
        print("\nEffective permissions for user:", user.email)
        for p in sorted(perms):
            print("-", p)

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    main()
