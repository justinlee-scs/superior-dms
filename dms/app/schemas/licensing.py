"""Pydantic schemas for the Licensing API (request/response shapes)."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.db.models.licensing import LicenseScope, LicenseStatus, MunicipalityType


# ---------- Province ----------

class ProvinceOut(BaseModel):
    id: str
    code: str
    name: str
    enabled: bool

    class Config:
        from_attributes = True


# ---------- Regional District ----------

class RegionalDistrictOut(BaseModel):
    id: str
    province_id: str
    name: str
    enabled: bool

    class Config:
        from_attributes = True


# ---------- Municipality ----------

class MunicipalityCreate(BaseModel):
    name: str
    municipality_type: MunicipalityType
    regional_district_id: str
    tracking_enabled: bool = True
    notes: Optional[str] = None


class MunicipalityUpdate(BaseModel):
    name: Optional[str] = None
    municipality_type: Optional[MunicipalityType] = None
    regional_district_id: Optional[str] = None
    tracking_enabled: Optional[bool] = None
    notes: Optional[str] = None


class MunicipalityOut(BaseModel):
    id: str
    name: str
    municipality_type: MunicipalityType
    regional_district_id: str
    tracking_enabled: bool
    notes: Optional[str] = None

    class Config:
        from_attributes = True


# ---------- License ----------

class LicenseCreate(BaseModel):
    scope: LicenseScope
    municipality_id: Optional[str] = None
    regional_district_id: Optional[str] = None
    license_number: Optional[str] = None
    issuing_authority: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: date
    cost: Optional[float] = None
    status_override: Optional[LicenseStatus] = None
    warning_threshold_days: Optional[int] = None
    document_reference: Optional[str] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def check_scope_target(self):
        if self.scope == LicenseScope.MUNICIPAL:
            if not self.municipality_id or self.regional_district_id:
                raise ValueError(
                    "Municipal-scope licenses require municipality_id and must not set regional_district_id."
                )
        elif self.scope == LicenseScope.INTERMUNICIPAL:
            if not self.regional_district_id or self.municipality_id:
                raise ValueError(
                    "Intermunicipal-scope licenses require regional_district_id and must not set municipality_id."
                )
        return self


class LicenseUpdate(BaseModel):
    license_number: Optional[str] = None
    issuing_authority: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    cost: Optional[float] = None
    status_override: Optional[LicenseStatus] = None
    warning_threshold_days: Optional[int] = None
    document_reference: Optional[str] = None
    notes: Optional[str] = None


class LicenseOut(BaseModel):
    id: str
    scope: LicenseScope
    municipality_id: Optional[str] = None
    regional_district_id: Optional[str] = None
    license_number: Optional[str] = None
    issuing_authority: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: date
    cost: Optional[float] = None
    status_override: Optional[LicenseStatus] = None
    warning_threshold_days: Optional[int] = None
    document_reference: Optional[str] = None
    notes: Optional[str] = None
    company_ids: list[str] = []

    # Computed (not a DB column) - filled in by the service layer
    computed_status: LicenseStatus
    days_until_expiry: int

    class Config:
        from_attributes = True


# ---------- Dashboard row (the main table the UI renders) ----------

class GovernmentLicenseRow(BaseModel):
    """
    One row per (municipality, applicable license) for the main dashboard
    table. A municipality may appear once if covered by an intermunicipal
    license, or with its own row if it has a direct municipal license.
    If a municipality has neither, it still appears with no license info
    so gaps are visible.
    """
    province_name: str
    region_name: str
    municipality_id: str
    municipality_name: str
    municipality_type: MunicipalityType
    tracking_enabled: bool

    license_id: Optional[str] = None
    license_scope: Optional[LicenseScope] = None
    license_number: Optional[str] = None
    expiry_date: Optional[date] = None
    status_override: Optional[LicenseStatus] = None
    computed_status: Optional[LicenseStatus] = None
    days_until_expiry: Optional[int] = None
    cost: Optional[float] = None
    covered_via_region: bool = False  # True if covered by an intermunicipal license
    company_ids: list[str] = []  # which companies this license is assigned to


class BulkToggleRequest(BaseModel):
    province_id: Optional[str] = None
    regional_district_id: Optional[str] = None
    tracking_enabled: bool

    @model_validator(mode="after")
    def check_target(self):
        if not self.province_id and not self.regional_district_id:
            raise ValueError("Provide either province_id or regional_district_id.")
        return self
    
# ---------- Company ----------

class CompanyOut(BaseModel):
    id: str
    name: str
    short_name: str
    enabled: bool

    class Config:
        from_attributes = True