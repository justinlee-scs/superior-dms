from app.db.session import SessionLocal
from app.db.seeds.permissions import seed_permissions
from app.db.seeds.roles import seed_roles


def main():
    db = SessionLocal()

    try:
        print("Seeding permissions...")
        seed_permissions(db)

        print("Seeding roles and role-permission mappings...")
        seed_roles(db)

        print("RBAC seeding complete.")
    except Exception as e:
        db.rollback()
        print("Error during seeding:", e)
    finally:
        db.close()


if __name__ == "__main__":
    main()
