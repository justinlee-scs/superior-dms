"""
SQLAlchemy models for Business License Tracking.

IMPORTANT: This module uses its OWN declarative Base and its OWN database
(`licensing_db`) - completely separate from the main DMS database, but on
the same Postgres instance/server. This means:
  - You can `pg_dump licensing_db` independently of the DMS database.
  - You need a separate SQLAlchemy engine/session pointed at licensing_db
    (see database.py).
  - Do NOT import or mix Base from the DMS's models module here.
"""

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def gen_uuid() -> str:
    return str(uuid.uuid4())


# Association table — links licenses to one or more companies.
# A license with one company entry = company-specific.
# A license with multiple company entries = shared between those companies.
# A license with no entries = unassigned.
license_companies = Table(
    "license_companies",
    Base.metadata,
    Column(
        "license_id", ForeignKey("licenses.id", ondelete="CASCADE"), primary_key=True
    ),
    Column(
        "company_id", ForeignKey("companies.id", ondelete="CASCADE"), primary_key=True
    ),
)


class MunicipalityType(str, enum.Enum):
    CITY = "City"
    DISTRICT_MUNICIPALITY = "District Municipality"
    TOWN = "Town"
    VILLAGE = "Village"
    ISLAND_MUNICIPALITY = "Island Municipality"
    MOUNTAIN_RESORT_MUNICIPALITY = "Mountain Resort Municipality"
    RESORT_MUNICIPALITY = "Resort Municipality"
    INDIAN_GOVERNMENT_DISTRICT = "Indian Government District"
    OTHER = "Other"


class LicenseScope(str, enum.Enum):
    MUNICIPAL = "Municipal"  # Covers a single municipality only
    INTERMUNICIPAL = "Intermunicipal"  # Covers an entire regional district


class LicenseStatus(str, enum.Enum):
    ACTIVE = "Active"
    EXPIRING_SOON = "Expiring Soon"
    EXPIRED = "Expired"
    INACTIVE = "Inactive"  # Manually deactivated / not pursued
    PENDING = "Pending"  # Applied for, not yet issued


class Province(Base):
    """
    Province/territory. Seeded with BC; structure supports expansion if
    the company starts operating in other provinces later.
    """

    __tablename__ = "provinces"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=gen_uuid
    )
    code: Mapped[str] = mapped_column(
        String(2), unique=True, nullable=False
    )  # e.g. "BC"
    name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g. "British Columbia"
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    regional_districts: Mapped[list["RegionalDistrict"]] = relationship(
        back_populates="province", cascade="all, delete-orphan"
    )


class RegionalDistrict(Base):
    """
    Official BC Regional District (or equivalent special-status area).
    A region can have its own intermunicipal license that covers every
    municipality within it.
    """

    __tablename__ = "regional_districts"
    __table_args__ = (
        UniqueConstraint("province_id", "name", name="uq_region_per_province"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=gen_uuid
    )
    province_id: Mapped[str] = mapped_column(ForeignKey("provinces.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    province: Mapped["Province"] = relationship(back_populates="regional_districts")
    municipalities: Mapped[list["Municipality"]] = relationship(
        back_populates="regional_district", cascade="all, delete-orphan"
    )
    licenses: Mapped[list["License"]] = relationship(
        back_populates="regional_district",
        foreign_keys="License.regional_district_id",
    )


class Municipality(Base):
    """
    A single municipality (city, district municipality, town, village, etc.)
    Editable/addable via the admin UI on top of the initial seed.
    """

    __tablename__ = "municipalities"
    __table_args__ = (
        # NOTE: name alone is not unique within a region - e.g. Metro
        # Vancouver has both a "North Vancouver" City and a "North
        # Vancouver" District Municipality (same for "Langley"). The
        # constraint includes municipality_type to allow this correctly.
        UniqueConstraint(
            "regional_district_id",
            "name",
            "municipality_type",
            name="uq_municipality_per_region",
        ),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=gen_uuid
    )
    regional_district_id: Mapped[str] = mapped_column(
        ForeignKey("regional_districts.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    municipality_type: Mapped[MunicipalityType] = mapped_column(
        Enum(MunicipalityType, name="municipality_type"), nullable=False
    )

    # "Tracking Status" - whether SCS currently cares about / tracks this
    # government for licensing purposes. Distinct from license status.
    # Bulk-toggleable by province or region.
    tracking_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    regional_district: Mapped["RegionalDistrict"] = relationship(
        back_populates="municipalities"
    )
    licenses: Mapped[list["License"]] = relationship(
        back_populates="municipality",
        foreign_keys="License.municipality_id",
        cascade="all, delete-orphan",
    )


class License(Base):
    """
    A business license record. Either:
      - scope=MUNICIPAL -> tied to a single municipality_id (regional_district_id NULL), or
      - scope=INTERMUNICIPAL -> tied to a regional_district_id (municipality_id NULL),
        covering every municipality in that region.

    Status is auto-calculated from expiry_date by default (see
    `compute_status` in licensing_service.py), but `status_override` lets
    a user manually force a status (e.g. mark something Inactive even
    though it hasn't expired, or Pending while an application is in review).
    """

    __tablename__ = "licenses"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=gen_uuid
    )

    scope: Mapped[LicenseScope] = mapped_column(
        Enum(LicenseScope, name="license_scope"), nullable=False
    )

    municipality_id: Mapped[str | None] = mapped_column(
        ForeignKey("municipalities.id"), nullable=True
    )
    regional_district_id: Mapped[str | None] = mapped_column(
        ForeignKey("regional_districts.id"), nullable=True
    )

    license_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    issuing_authority: Mapped[str | None] = mapped_column(String(150), nullable=True)

    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)

    cost: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    # If set, this overrides the auto-calculated status entirely.
    status_override: Mapped[LicenseStatus | None] = mapped_column(
        Enum(LicenseStatus, name="license_status"), nullable=True
    )

    # Threshold (days) for "expiring soon" warning, per-license override.
    # Falls back to a system-wide default (e.g. 30 days) if NULL.
    warning_threshold_days: Mapped[int | None] = mapped_column(nullable=True)

    document_reference: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )  # e.g. link/path to the DMS document for this license, if linked

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    municipality: Mapped["Municipality | None"] = relationship(
        back_populates="licenses", foreign_keys=[municipality_id]
    )
    regional_district: Mapped["RegionalDistrict | None"] = relationship(
        back_populates="licenses", foreign_keys=[regional_district_id]
    )

    companies: Mapped[list["Company"]] = relationship(
        secondary=license_companies, back_populates="licenses"
    )


class Company(Base):
    """
    A company entity (e.g. Superior City Services, Superior City Contracting Services).
    Licenses are associated to one or more companies via the license_companies join table.
    """

    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=gen_uuid
    )
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    short_name: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False
    )  # e.g. "SCS"
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    licenses: Mapped[list["License"]] = relationship(
        secondary=license_companies, back_populates="companies"
    )
