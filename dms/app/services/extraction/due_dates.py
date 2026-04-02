from __future__ import annotations

import re
from datetime import date, datetime

_DUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?:due date|payment due|payable by|due by|due on)\\s*[:\\-]?\\s*(\\d{4}-\\d{1,2}-\\d{1,2})", re.IGNORECASE),
    re.compile(r"(?:due date|payment due|payable by|due by|due on)\\s*[:\\-]?\\s*(\\d{1,2}[/-]\\d{1,2}[/-]\\d{2,4})", re.IGNORECASE),
    re.compile(r"(?:due date|payment due|payable by|due by|due on)\\s*[:\\-]?\\s*([A-Za-z]{3,9}\\s+\\d{1,2},?\\s+\\d{2,4})", re.IGNORECASE),
    re.compile(r"(?:due date|payment due|payable by|due by|due on)\\s*[:\\-]?\\s*(\\d{1,2}\\s+[A-Za-z]{3,9}\\s+\\d{2,4})", re.IGNORECASE),
)

_DATE_FORMATS: tuple[str, ...] = (
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%m/%d/%y",
    "%m-%d-%Y",
    "%m-%d-%y",
    "%b %d, %Y",
    "%B %d, %Y",
    "%b %d %Y",
    "%B %d %Y",
    "%d %b %Y",
    "%d %B %Y",
)


def _parse_date(value: str) -> date | None:
    cleaned = value.strip().replace("  ", " ")
    cleaned = re.sub(r"[\\s,]+$", "", cleaned)
    for fmt in _DATE_FORMATS:
        try:
            parsed = datetime.strptime(cleaned, fmt).date()
            if parsed.year < 100:
                parsed = parsed.replace(year=2000 + parsed.year)
            return parsed
        except ValueError:
            continue
    return None


def extract_due_date(text: str) -> date | None:
    """Extract a due date from OCR text, preferring explicit due-date labels."""
    if not text:
        return None
    matches: list[date] = []
    for pattern in _DUE_PATTERNS:
        for match in pattern.finditer(text):
            value = match.group(1)
            parsed = _parse_date(value)
            if parsed:
                matches.append(parsed)
    if not matches:
        return None
    return min(matches)
