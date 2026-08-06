"""Business logic for license status computation and dashboard assembly."""

from datetime import date

from app.db.models.licensing import License, LicenseStatus

DEFAULT_WARNING_THRESHOLD_DAYS = 30


def compute_status(lic: License, today: date | None = None) -> tuple[LicenseStatus, int]:
    """
    Returns (status, days_until_expiry).
    days_until_expiry is negative if already expired.

    If lic.status_override is set, it wins outright (still returns the
    real days_until_expiry for display purposes).
    """
    today = today or date.today()
    days_until_expiry = (lic.expiry_date - today).days

    if lic.status_override is not None:
        return lic.status_override, days_until_expiry

    threshold = lic.warning_threshold_days or DEFAULT_WARNING_THRESHOLD_DAYS

    if days_until_expiry < 0:
        return LicenseStatus.EXPIRED, days_until_expiry
    if days_until_expiry <= threshold:
        return LicenseStatus.EXPIRING_SOON, days_until_expiry
    return LicenseStatus.ACTIVE, days_until_expiry