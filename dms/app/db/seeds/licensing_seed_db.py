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

def seed_imbl_regions(db, municipality_lookup: dict[str, str]):
    """
    Seed IMBL regions and their municipality memberships.
    municipality_lookup: dict of municipality name → municipality id
    """
    from app.db.models.licensing import ImblRegion, imbl_region_municipalities
    from sqlalchemy import insert

    # Skip if already seeded
    if db.query(ImblRegion).first():
        return

    IMBL_DATA = {
        "Metro West": [
            "Burnaby", "Delta", "New Westminster", "Richmond", "Surrey", "Vancouver",
        ],
        "Fraser Valley": [
            "Abbotsford", "Chilliwack", "Delta", "Harrison Hot Springs", "Hope",
            "Kent", "Langley", "Maple Ridge", "Mission", "Pitt Meadows", "Surrey",
        ],
        "Tri-Cities": ["Coquitlam", "Port Coquitlam", "Port Moody"],
        "North Shore": ["North Vancouver", "West Vancouver"],
        "Sunshine Coast": ["Gibsons", "Sechelt", "shishalh Nation"],
        "Greater Victoria": [
            "Central Saanich", "Colwood", "Esquimalt", "Highlands", "Langford",
            "Metchosin", "North Saanich", "Oak Bay", "Saanich", "Sidney",
            "Sooke", "Victoria", "View Royal",
        ],
        "Central Vancouver Island": [
            "Campbell River", "Comox", "Courtenay", "Cumberland", "Duncan",
            "Ladysmith", "Lake Cowichan", "Nanaimo", "North Cowichan",
            "Parksville", "Port Alberni", "Qualicum Beach",
        ],
        "Cowichan Valley": ["Duncan", "Ladysmith", "Lake Cowichan", "North Cowichan"],
        "Comox Valley": ["Comox", "Courtenay"],
        "Okanagan-Similkameen": [
            "Armstrong", "Coldstream", "Enderby", "Kelowna", "Keremeos",
            "Lake Country", "Lumby", "Merritt", "Oliver", "Osoyoos",
            "Peachland", "Penticton", "Princeton", "Revelstoke", "Salmon Arm",
            "Sicamous", "Spallumcheen", "Summerland", "Vernon", "West Kelowna",
        ],
        "Thompson-Nicola": [
            "Kamloops", "Merritt", "Barriere", "Clearwater", "Lillooet",
            "Logan Lake", "Chase",
        ],
        "Cranbrook / Kimberley": ["Cranbrook", "Kimberley"],
        "Elk Valley": ["Elkford", "Fernie", "Sparwood"],
        "Greater Trail": ["Fruitvale", "Montrose", "Rossland", "Trail", "Warfield"],
        "Kootenay": [
            "Castlegar", "Creston", "Grand Forks", "Kaslo", "Nelson",
            "New Denver", "Rossland", "Salmo", "Silverton", "Slocan",
        ],
        "Northeast BC": [
            "Chetwynd", "Dawson Creek", "Fort St. John", "Hudson's Hope",
            "Pouce Coupe", "Taylor", "Tumbler Ridge",
        ],
    }

    for region_name, members in IMBL_DATA.items():
        region = ImblRegion(name=region_name, enabled=True)
        db.add(region)
        db.flush()
        for muni_name in members:
            muni_id = municipality_lookup.get(muni_name)
            if muni_id:
                db.execute(
                    insert(imbl_region_municipalities).values(
                        imbl_region_id=region.id,
                        municipality_id=muni_id,
                    ).prefix_with("OR IGNORE")
                )
    print(f"Seeded {len(IMBL_DATA)} IMBL regions.")

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
        
        # Build municipality lookup for IMBL seeding
        all_munis = db.scalars(select(Municipality)).all()
        municipality_lookup = {m.name: m.id for m in all_munis}
        seed_imbl_regions(db, municipality_lookup)

        db.commit()
        
        db.commit()
        print(f"Seeded 1 province, {len(REGIONAL_DISTRICTS)} regional districts, {count} municipalities.")

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Drop and reseed everything")
    args = parser.parse_args()
    main(reset=args.reset)