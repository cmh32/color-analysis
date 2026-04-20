import os

import pytest

from color_analysis.storage.r2 import R2Client


@pytest.mark.skipif(os.getenv("COLOR_ANALYSIS_RUN_STORAGE_TESTS") != "1", reason="requires local MinIO")
def test_presigned_post() -> None:
    client = R2Client()
    payload = client.put_presigned_post("sessions/test/object.jpg")

    assert "url" in payload
    assert "fields" in payload
