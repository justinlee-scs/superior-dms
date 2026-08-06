"""
One-time (or --reset) seed script for the licensing_db database.

Usage:
    python seed_db.py            # seed only if empty (safe to re-run)
    python seed_db.py --reset    # wipe and reseed everything (DESTRUCTIVE)

Before running, make sure:
  1. licensing_db exists on your Postgres instance:
       CREATE DATABASE licensing_db;
  2. LICENSING_DATABASE_URL env var is set (or edit database.py's default)
  3. Tables are created (this script calls Base.metadata.create_all,
     so no separate migration step is required for first run).
"""

import argparse
import sys

from sqlalchemy import select

from app.db.session import LicensingSessionLocal, licensing_engine
from app.db.models.licensing import Base, Municipality, Province, RegionalDistrict, Company
from app.db.seeds.licensing_seed_data import MUNICIPALITIES, REGIONAL_DISTRICTS


def main(reset: bool = False):
    if reset:
        confirm = input(
            "This will DROP ALL TABLES in licensing_db and reseed. Type 'yes' to confirm: "
        )
        if confirm.strip().lower() != "yes":
            print("Aborted.")
            sys.exit(1)
        Base.metadata.drop_all(bind=licensing_engine)

    Base.metadata.create_all(bind=licensing_engine)

    db = LicensingSessionLocal()
    try:
        existing_province = db.scalar(select(Province).where(Province.code == "BC"))
        if existing_province and not reset:
            print("BC province already seeded. Skipping. Use --reset to reseed from scratch.")
            return

        if not existing_province:
            bc = Province(code="BC", name="British Columbia", enabled=True)
            db.add(bc)
            db.flush()
        else:
            bc = existing_province

        region_lookup: dict[str, RegionalDistrict] = {}
        for region_name in REGIONAL_DISTRICTS:
            region = RegionalDistrict(province_id=bc.id, name=region_name, enabled=True)
            db.add(region)
            region_lookup[region_name] = region
        db.flush()

        count = 0
        for name, mtype, region_name in MUNICIPALITIES:
            region = region_lookup[region_name]
            municipality = Municipality(
                regional_district_id=region.id,
                name=name,
                municipality_type=mtype,
                tracking_enabled=True,
            )
            db.add(municipality)
            count += 1
            
        scs = Company(name="Superior City Services", short_name="SCS", enabled=True)
        sccs = Company(name="Superior City Contracting Services", short_name="SCCS", enabled=True)
        db.add(scs)
        db.add(sccs)
        
        db.commit()
        print(f"Seeded 1 province, {len(REGIONAL_DISTRICTS)} regional districts, {count} municipalities.")

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Drop and reseed everything")
    args = parser.parse_args()
    main(reset=args.reset)