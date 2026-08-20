"""
FastAPI router for Business License Tracking.

Mount this in your main DMS app, e.g. in your main.py / app.py:

    from licensing_router import router as licensing_router
    app.include_router(licensing_router)

This router uses its own DB dependency (get_licensing_db) pointed at the
separate licensing_db database, but expects the SAME auth dependency as
the rest of your DMS so logins/sessions are shared. Replace
`get_current_user` below with your actual auth dependency import.
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_licensing_db
from app.services.licensing_service import compute_status
from app.db.models.licensing import (
    License,
    LicenseScope,
    LicenseStatus,
    Municipality,
    Province,
    RegionalDistrict,
    Company,
    license_companies,
    ImblRegion,
    imbl_region_municipalities,
)
from app.schemas.licensing import (
    BulkToggleRequest,
    CompanyOut,
    GovernmentLicenseRow,
    ImblRegionOut,
    ImblRegionCreate,
    ImblRegionUpdate,
    LicenseCreate,
    LicenseOut,
    LicenseUpdate,
    MunicipalityCreate,
    MunicipalityOut,
    MunicipalityUpdate,
    ProvinceOut,
    RegionalDistrictOut,
)
from app.auth.deps import get_current_user


# --- Replace this with your real auth dependency ---
# from auth import get_current_user
def get_current_user():
    """Placeholder - swap for your actual DMS auth dependency."""
    return {"id": "stub-user"}


# -----------------------------------------------------

router = APIRouter(
    prefix="/licensing",
    tags=["licensing"],
    dependencies=[Depends(get_current_user)],
)


# ============================================================
# Provinces
# ============================================================


@router.get("/provinces", response_model=list[ProvinceOut])
def list_provinces(db: Session = Depends(get_licensing_db)):
    return db.scalars(select(Province).order_by(Province.name)).all()


# ============================================================
# Companies
# ============================================================


@router.get("/companies", response_model=list[CompanyOut])
def list_companies(db: Session = Depends(get_licensing_db)):
    return db.scalars(
        select(Company).where(Company.enabled == True).order_by(Company.name)
    ).all()


# ============================================================
# IMBL Regions
# ============================================================


@router.get("/imbl-regions", response_model=list[ImblRegionOut])
def list_imbl_regions(db: Session = Depends(get_licensing_db)):
    return db.scalars(
        select(ImblRegion).where(ImblRegion.enabled == True).order_by(ImblRegion.name)
    ).all()


@router.post("/imbl-regions", response_model=ImblRegionOut, status_code=201)
def create_imbl_region(
    payload: ImblRegionCreate, db: Session = Depends(get_licensing_db)
):
    region = ImblRegion(name=payload.name, enabled=True)
    db.add(region)
    db.commit()
    db.refresh(region)
    return region


@router.patch("/imbl-regions/{imbl_region_id}", response_model=ImblRegionOut)
def update_imbl_region(
    imbl_region_id: str,
    payload: ImblRegionUpdate,
    db: Session = Depends(get_licensing_db),
):
    region = db.get(ImblRegion, imbl_region_id)
    if not region:
        raise HTTPException(404, "IMBL region not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(region, field, value)
    db.commit()
    db.refresh(region)
    return region


@router.delete("/imbl-regions/{imbl_region_id}", status_code=204)
def delete_imbl_region(imbl_region_id: str, db: Session = Depends(get_licensing_db)):
    region = db.get(ImblRegion, imbl_region_id)
    if not region:
        raise HTTPException(404, "IMBL region not found")
    db.delete(region)
    db.commit()


@router.post(
    "/imbl-regions/{imbl_region_id}/municipalities/{municipality_id}", status_code=200
)
def add_municipality_to_imbl_region(
    imbl_region_id: str, municipality_id: str, db: Session = Depends(get_licensing_db)
):
    region = db.get(ImblRegion, imbl_region_id)
    if not region:
        raise HTTPException(404, "IMBL region not found")
    muni = db.get(Municipality, municipality_id)
    if not muni:
        raise HTTPException(404, "Municipality not found")
    if muni not in region.municipalities:
        region.municipalities.append(muni)
        db.commit()
    return {"ok": True}


@router.delete(
    "/imbl-regions/{imbl_region_id}/municipalities/{municipality_id}", status_code=200
)
def remove_municipality_from_imbl_region(
    imbl_region_id: str, municipality_id: str, db: Session = Depends(get_licensing_db)
):
    region = db.get(ImblRegion, imbl_region_id)
    if not region:
        raise HTTPException(404, "IMBL region not found")
    muni = db.get(Municipality, municipality_id)
    if muni and muni in region.municipalities:
        region.municipalities.remove(muni)
        db.commit()
    return {"ok": True}


# ============================================================
# Regional Districts
# ============================================================


@router.get("/regional-districts", response_model=list[RegionalDistrictOut])
def list_regional_districts(
    province_id: Optional[str] = None,
    db: Session = Depends(get_licensing_db),
):
    stmt = select(RegionalDistrict).order_by(RegionalDistrict.name)
    if province_id:
        stmt = stmt.where(RegionalDistrict.province_id == province_id)
    return db.scalars(stmt).all()


# ============================================================
# Municipalities
# ============================================================


@router.get("/municipalities", response_model=list[MunicipalityOut])
def list_municipalities(
    regional_district_id: Optional[str] = None,
    search: Optional[str] = Query(None, description="Case-insensitive name search"),
    tracking_enabled: Optional[bool] = None,
    db: Session = Depends(get_licensing_db),
):
    stmt = select(Municipality).order_by(Municipality.name)
    if regional_district_id:
        stmt = stmt.where(Municipality.regional_district_id == regional_district_id)
    if search:
        stmt = stmt.where(Municipality.name.ilike(f"%{search}%"))
    if tracking_enabled is not None:
        stmt = stmt.where(Municipality.tracking_enabled == tracking_enabled)
    return db.scalars(stmt).all()


@router.post("/municipalities", response_model=MunicipalityOut, status_code=201)
def create_municipality(
    payload: MunicipalityCreate, db: Session = Depends(get_licensing_db)
):
    region = db.get(RegionalDistrict, payload.regional_district_id)
    if not region:
        raise HTTPException(404, "Regional district not found")
    m = Municipality(**payload.model_dump())
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@router.patch("/municipalities/{municipality_id}", response_model=MunicipalityOut)
def update_municipality(
    municipality_id: str,
    payload: MunicipalityUpdate,
    db: Session = Depends(get_licensing_db),
):
    m = db.get(Municipality, municipality_id)
    if not m:
        raise HTTPException(404, "Municipality not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(m, field, value)
    db.commit()
    db.refresh(m)
    return m


@router.delete("/municipalities/{municipality_id}", status_code=204)
def delete_municipality(municipality_id: str, db: Session = Depends(get_licensing_db)):
    m = db.get(Municipality, municipality_id)
    if not m:
        raise HTTPException(404, "Municipality not found")
    db.delete(m)
    db.commit()


@router.post("/municipalities/bulk-toggle", status_code=200)
def bulk_toggle_tracking(
    payload: BulkToggleRequest, db: Session = Depends(get_licensing_db)
):
    """Enable/disable tracking for every municipality in a province or region."""
    stmt = select(Municipality)
    if payload.regional_district_id:
        stmt = stmt.where(
            Municipality.regional_district_id == payload.regional_district_id
        )
    elif payload.province_id:
        stmt = stmt.join(RegionalDistrict).where(
            RegionalDistrict.province_id == payload.province_id
        )

    municipalities = db.scalars(stmt).all()
    for m in municipalities:
        m.tracking_enabled = payload.tracking_enabled
    db.commit()
    return {"updated_count": len(municipalities)}


# ============================================================
# Licenses
# ============================================================


def _to_license_out(lic: License) -> LicenseOut:
    status, days = compute_status(lic)
    return LicenseOut(
        **{c.name: getattr(lic, c.name) for c in License.__table__.columns},
        computed_status=status,
        days_until_expiry=days,
        company_ids=[c.id for c in lic.companies],
        issuing_municipality_name=(
            lic.issuing_municipality.name if lic.issuing_municipality else None
        ),
        imbl_region_name=lic.imbl_region.name if lic.imbl_region else None,
    )


@router.get("/licenses", response_model=list[LicenseOut])
def list_licenses(
    municipality_id: Optional[str] = None,
    regional_district_id: Optional[str] = None,
    company_id: Optional[str] = None,
    db: Session = Depends(get_licensing_db),
):
    stmt = select(License)
    if municipality_id:
        stmt = stmt.where(License.municipality_id == municipality_id)
    if regional_district_id:
        stmt = stmt.where(License.regional_district_id == regional_district_id)
    if company_id:
        stmt = stmt.join(license_companies).where(
            license_companies.c.company_id == company_id
        )
    licenses = db.scalars(stmt).all()
    return [_to_license_out(lic) for lic in licenses]


@router.post("/licenses", response_model=LicenseOut, status_code=201)
def create_license(payload: LicenseCreate, db: Session = Depends(get_licensing_db)):
    if payload.scope == LicenseScope.MUNICIPAL:
        if not db.get(Municipality, payload.municipality_id):
            raise HTTPException(404, "Municipality not found")
    else:
        if not db.get(RegionalDistrict, payload.regional_district_id):
            raise HTTPException(404, "Regional district not found")

    lic = License(**payload.model_dump())
    db.add(lic)
    db.commit()
    db.refresh(lic)
    return _to_license_out(lic)


@router.patch("/licenses/{license_id}", response_model=LicenseOut)
def update_license(
    license_id: str, payload: LicenseUpdate, db: Session = Depends(get_licensing_db)
):
    lic = db.get(License, license_id)
    if not lic:
        raise HTTPException(404, "License not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(lic, field, value)
    db.commit()
    db.refresh(lic)
    return _to_license_out(lic)


@router.delete("/licenses/{license_id}", status_code=204)
def delete_license(license_id: str, db: Session = Depends(get_licensing_db)):
    lic = db.get(License, license_id)
    if not lic:
        raise HTTPException(404, "License not found")
    db.delete(lic)
    db.commit()


@router.post("/licenses/{license_id}/companies/{company_id}", status_code=200)
def add_company_to_license(
    license_id: str, company_id: str, db: Session = Depends(get_licensing_db)
):
    lic = db.get(License, license_id)
    if not lic:
        raise HTTPException(404, "License not found")
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(404, "Company not found")
    if company not in lic.companies:
        lic.companies.append(company)
        db.commit()
    return {"ok": True}


@router.delete("/licenses/{license_id}/companies/{company_id}", status_code=200)
def remove_company_from_license(
    license_id: str, company_id: str, db: Session = Depends(get_licensing_db)
):
    lic = db.get(License, license_id)
    if not lic:
        raise HTTPException(404, "License not found")
    company = db.get(Company, company_id)
    if company and company in lic.companies:
        lic.companies.remove(company)
        db.commit()
    return {"ok": True}


# ============================================================
# Dashboard (the main table view)
# ============================================================


@router.get("/dashboard", response_model=list[GovernmentLicenseRow])
def get_dashboard(
    status_filter: Optional[str] = Query(
        None, description="'active' | 'inactive' | 'all' (default: all)"
    ),
    province_id: Optional[str] = None,
    regional_district_id: Optional[str] = None,
    search: Optional[str] = None,
    company_id: Optional[str] = None,
    tracking_enabled_only: bool = Query(
        True,
        description="If true (default), only show municipalities with tracking enabled",
    ),
    db: Session = Depends(get_licensing_db),
):
    """
    Builds one row per tracked municipality, joined with whichever license
    applies to it - either a direct municipal license, or an intermunicipal
    license covering its region (region-level license wins display-wise
    if both exist, since it's the broader/active coverage).
    """
    muni_stmt = select(Municipality).join(RegionalDistrict).join(Province)
    if province_id:
        muni_stmt = muni_stmt.where(RegionalDistrict.province_id == province_id)
    if regional_district_id:
        muni_stmt = muni_stmt.where(
            Municipality.regional_district_id == regional_district_id
        )
    if search:
        muni_stmt = muni_stmt.where(Municipality.name.ilike(f"%{search}%"))
    if tracking_enabled_only:
        muni_stmt = muni_stmt.where(Municipality.tracking_enabled == True)  # noqa: E712

    municipalities = db.scalars(muni_stmt).all()

    # Preload all licenses, grouped by municipality_id and regional_district_id
    all_licenses = db.scalars(select(License)).all()
    # If filtering by company, only consider licenses assigned to that company
    if company_id:
        all_licenses = [
            lic
            for lic in all_licenses
            if any(c.id == company_id for c in lic.companies)
        ]

    # Build lookups: municipality_id → best license, region_id → best license
    by_municipality: dict[str, License] = {}
    by_region: dict[str, License] = {}
    # NEW: IMBL coverage — imbl_region_id → license, then expand to all member municipalities
    by_imbl_region: dict[str, License] = {}

    for lic in all_licenses:
        if lic.scope == LicenseScope.MUNICIPAL and lic.municipality_id:
            # If multiple, keep the one with the latest expiry (most relevant/current)
            existing = by_municipality.get(lic.municipality_id)
            if not existing or lic.expiry_date > existing.expiry_date:
                by_municipality[lic.municipality_id] = lic
        elif lic.scope == LicenseScope.INTERMUNICIPAL:
            if lic.imbl_region_id:
                existing = by_imbl_region.get(lic.imbl_region_id)
                if not existing or lic.expiry_date > existing.expiry_date:
                    by_imbl_region[lic.imbl_region_id] = lic
            elif lic.regional_district_id:
                existing = by_region.get(lic.regional_district_id)
                if not existing or lic.expiry_date > existing.expiry_date:
                    by_region[lic.regional_district_id] = lic

    # Preload IMBL region membership for all municipalities
    all_imbl_regions = db.scalars(select(ImblRegion)).all()
    # municipality_id → list of ImblRegion
    muni_to_imbl: dict[str, list[ImblRegion]] = {}
    for imbl in all_imbl_regions:
        for m in imbl.municipalities:
            muni_to_imbl.setdefault(m.id, []).append(imbl)

    rows: list[GovernmentLicenseRow] = []
    for m in municipalities:
        region = m.regional_district
        province = region.province

        # Prefer a direct municipal license; fall back to regional intermunicipal coverage
        # Coverage priority:
        # 1. Direct municipal license
        # 2. IMBL intermunicipal license covering this municipality's IMBL region(s)
        # 3. Regional district intermunicipal license
        lic = by_municipality.get(m.id)
        covered_via_region = False
        imbl_license = None
        imbl_region_for_coverage = None

        if not lic:
            # Check IMBL coverage
            for imbl_region in muni_to_imbl.get(m.id, []):
                if imbl_region.id in by_imbl_region:
                    imbl_license = by_imbl_region[imbl_region.id]
                    imbl_region_for_coverage = imbl_region
                    covered_via_region = True
                    break

        if not lic and not imbl_license:
            # Fall back to regional district coverage
            lic = by_region.get(m.regional_district_id)
            covered_via_region = lic is not None

        effective_lic = lic or imbl_license
        if effective_lic:
            computed, days = compute_status(effective_lic)
        else:
            computed, days = None, None

        imbl_regions_for_muni = muni_to_imbl.get(m.id, [])

        row = GovernmentLicenseRow(
            province_name=province.name,
            region_name=region.name,
            municipality_id=m.id,
            municipality_name=m.name,
            municipality_type=m.municipality_type,
            tracking_enabled=m.tracking_enabled,
            license_id=effective_lic.id if effective_lic else None,
            license_scope=effective_lic.scope if effective_lic else None,
            license_number=effective_lic.license_number if effective_lic else None,
            expiry_date=effective_lic.expiry_date if effective_lic else None,
            computed_status=computed,
            days_until_expiry=days,
            covered_via_region=covered_via_region,
            cost=effective_lic.cost if effective_lic else None,
            company_ids=[c.id for c in effective_lic.companies] if effective_lic else [],
            status_override=effective_lic.status_override if effective_lic else None,
            imbl_region_ids=[ir.id for ir in imbl_regions_for_muni],
            imbl_region_names=[ir.name for ir in imbl_regions_for_muni],
            issuing_municipality_id=effective_lic.issuing_municipality_id if effective_lic else None,
            issuing_municipality_name=effective_lic.issuing_municipality.name if effective_lic and effective_lic.issuing_municipality else None,
            imbl_region_id=imbl_region_for_coverage.id if imbl_region_for_coverage else (effective_lic.imbl_region_id if effective_lic else None),
            imbl_region_name=imbl_region_for_coverage.name if imbl_region_for_coverage else (effective_lic.imbl_region.name if effective_lic and effective_lic.imbl_region else None),
        )

        # Apply status_filter AFTER computing status
        if status_filter == "active" and computed not in (
            LicenseStatus.ACTIVE,
            LicenseStatus.EXPIRING_SOON,
        ):
            continue
        if status_filter == "inactive" and computed not in (
            LicenseStatus.EXPIRED,
            LicenseStatus.INACTIVE,
            None,
        ):
            continue

        rows.append(row)

    return rows


@router.get("/expiring-soon", response_model=list[GovernmentLicenseRow])
def get_expiring_soon(
    within_days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_licensing_db),
):
    """Convenience endpoint for a warning banner / notification widget."""
    all_rows = get_dashboard(
        status_filter="all",
        province_id=None,
        regional_district_id=None,
        search=None,
        tracking_enabled_only=True,
        db=db,
    )
    today = date.today()
    return [
        r
        for r in all_rows
        if r.days_until_expiry is not None and 0 <= r.days_until_expiry <= within_days
    ]


@router.post("/provinces", response_model=ProvinceOut, status_code=201)
def create_province(payload: dict, db: Session = Depends(get_licensing_db)):
    from app.db.models.licensing import Province

    p = Province(name=payload["name"], code=payload["code"], enabled=True)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.post("/regional-districts", response_model=RegionalDistrictOut, status_code=201)
def create_regional_district(payload: dict, db: Session = Depends(get_licensing_db)):
    p = RegionalDistrict(
        name=payload["name"], province_id=payload["province_id"], enabled=True
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p
