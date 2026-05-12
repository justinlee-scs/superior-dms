#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

from alembic.autogenerate import api as autogen_api
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

from app.db.base import Base
import app.db.models  # noqa: F401


def main() -> int:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is not set.", file=sys.stderr)
        return 2

    engine = create_engine(database_url)
    with engine.connect() as connection:
        context = MigrationContext.configure(
            connection=connection,
            opts={
                "compare_type": True,
                "compare_server_default": True,
                "target_metadata": Base.metadata,
            },
        )
        diffs = autogen_api.compare_metadata(context, Base.metadata)

    if diffs:
        print("Schema drift detected: model metadata differs from DB schema.", file=sys.stderr)
        for diff in diffs:
            print(f"- {diff}", file=sys.stderr)
        print(
            "Create and commit an Alembic migration: alembic revision --autogenerate -m '<message>'",
            file=sys.stderr,
        )
        return 1

    print("No schema drift detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
