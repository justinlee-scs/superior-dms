from uuid import UUID

import pytest

from app.db.models.ocr_correction import (
    ExtractionFieldCorrection,
    OCRCorrectionQueue,
    OCRWordBox,
)


@pytest.mark.parametrize(
    "model",
    [OCRCorrectionQueue, OCRWordBox, ExtractionFieldCorrection],
)
def test_correction_table_ids_have_python_and_postgres_defaults(model):
    id_column = model.__table__.c.id
    assert id_column.default is not None
    assert isinstance(id_column.default.arg(None), UUID)
    assert id_column.server_default is not None
    assert str(id_column.server_default.arg) == "gen_random_uuid()"
