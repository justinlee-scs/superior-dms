from sqlalchemy.orm import Session
from app.db.models.role import Role
from app.db.models.permission import Permission


def seed_admin_role(db: Session):
    admin = db.query(Role).filter_by(name="Admin").first()
    if not admin:
        admin = Role(name="Admin", description="System administrator")
        db.add(admin)
        db.commit()

    permissions = db.query(Permission).all()
    admin.permissions = permissions
    db.commit()
