from __future__ import annotations

import sys
from pathlib import Path


SUITE_ROOT = Path(__file__).resolve().parent
DMS_ROOT = SUITE_ROOT.parent / "dms"

if str(DMS_ROOT) not in sys.path:
    sys.path.insert(0, str(DMS_ROOT))
