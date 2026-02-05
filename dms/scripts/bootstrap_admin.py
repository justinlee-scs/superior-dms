import sys
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models.user import User
from app.db.models.role import Role
from app.services.security import hash_password


ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "change-me-now"
ADMIN_ROLE_NAME = "admin"


def get_or_create_role(db: Session, name: str) -> Role:
    role = db.query(Role).filter(Role.name == name).first()
    if role:
        return role

    role = Role(name=name)
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


def main():
    db: Session = SessionLocal()

    try:
        existing = db.query(User).first()
        if existing:
            print("Users already exist. Aborting.")
            sys.exit(1)

        admin_role = get_or_create_role(db, ADMIN_ROLE_NAME)

        user = User(
            email=ADMIN_EMAIL,
            hashed_password=hash_password(ADMIN_PASSWORD),
            is_active=True,
        )
        user.roles.append(admin_role)

        db.add(user)
        db.commit()

        print("Admin user created.")
        print(f"Email: {ADMIN_EMAIL}")
        print("Password: change-me-now")

    finally:
        db.close()


if __name__ == "__main__":
    main()
