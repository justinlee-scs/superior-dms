import sys
from pathlib import Path

# Ensure project root is on PYTHONPATH
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

import uuid
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models.user import User
from app.db.models.role import Role
from app.auth.jwt import hash_password


ADMIN_EMAIL = "justin.lee@scsgroup.ca"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "jlscspass"
ADMIN_ROLE_NAME = "admin"


def main() -> None:
    db: Session = SessionLocal()

    try:
        # ---- role ----
        role = (
            db.query(Role)
            .filter(Role.name == ADMIN_ROLE_NAME)
            .one_or_none()
        )

        if role is None:
            role = Role(name=ADMIN_ROLE_NAME)
            db.add(role)
            db.flush()  # ensures role.id exists

        # ---- user ----
        user = (
            db.query(User)
            .filter(User.email == ADMIN_EMAIL)
            .one_or_none()
        )

        if user is None:
            user = User(
                id=uuid.uuid4(),
                username=ADMIN_USERNAME,        # ← REQUIRED
                email=ADMIN_EMAIL,
                hashed_password=hash_password(ADMIN_PASSWORD),
                is_active=True,
            )
            db.add(user)
            db.flush()

        # ---- role assignment ----
        if role not in user.roles:
            user.roles.append(role)

        db.commit()
        print("Admin user bootstrapped successfully.")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
