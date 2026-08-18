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
)
from app.schemas.licensing import (
    BulkToggleRequest,
    CompanyOut,
    GovernmentLicenseRow,
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
    by_municipality: dict[str, License] = {}
    by_region: dict[str, License] = {}
    for lic in all_licenses:
        if lic.scope == LicenseScope.MUNICIPAL and lic.municipality_id:
            # If multiple, keep the one with the latest expiry (most relevant/current)
            existing = by_municipality.get(lic.municipality_id)
            if not existing or lic.expiry_date > existing.expiry_date:
                by_municipality[lic.municipality_id] = lic
        elif lic.scope == LicenseScope.INTERMUNICIPAL and lic.regional_district_id:
            existing = by_region.get(lic.regional_district_id)
            if not existing or lic.expiry_date > existing.expiry_date:
                by_region[lic.regional_district_id] = lic

    rows: list[GovernmentLicenseRow] = []
    for m in municipalities:
        region = m.regional_district
        province = region.province

        # Prefer a direct municipal license; fall back to regional intermunicipal coverage
        lic = by_municipality.get(m.id)
        covered_via_region = False
        if not lic:
            lic = by_region.get(m.regional_district_id)
            covered_via_region = lic is not None

        if lic:
            computed, days = compute_status(lic)
        else:
            computed, days = None, None

        row = GovernmentLicenseRow(
            province_name=province.name,
            region_name=region.name,
            municipality_id=m.id,
            municipality_name=m.name,
            municipality_type=m.municipality_type,
            tracking_enabled=m.tracking_enabled,
            license_id=lic.id if lic else None,
            license_scope=lic.scope if lic else None,
            license_number=lic.license_number if lic else None,
            status_override=lic.status_override if lic else None,
            expiry_date=lic.expiry_date if lic else None,
            computed_status=computed,
            days_until_expiry=days,
            cost=lic.cost if lic else None,
            company_ids=[c.id for c in lic.companies] if lic else [],
            covered_via_region=covered_via_region,
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
