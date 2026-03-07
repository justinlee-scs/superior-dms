from alembic import command
from alembic.config import Config


def init_db() -> None:
    """Apply all database migrations to head."""
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")


if __name__ == "__main__":
    init_db()
