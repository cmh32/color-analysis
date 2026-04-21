import os
from unittest.mock import Mock

import pytest
from botocore.exceptions import ClientError

from color_analysis.storage.r2 import R2Client


@pytest.mark.skipif(os.getenv("COLOR_ANALYSIS_RUN_STORAGE_TESTS") != "1", reason="requires local MinIO")
def test_presigned_post() -> None:
    client = R2Client()
    payload = client.put_presigned_post("sessions/test/object.jpg")

    assert "url" in payload
    assert "fields" in payload


def _client_error(code: str) -> ClientError:
    return ClientError({"Error": {"Code": code}}, "HeadBucket")


def test_ensure_bucket_exists_creates_when_missing() -> None:
    client = R2Client()
    mock = Mock()
    mock.head_bucket.side_effect = [_client_error("404"), {}]
    client.client = mock
    client.bucket = "color-analysis"

    client.ensure_bucket_exists()

    assert mock.head_bucket.call_count == 2
    mock.create_bucket.assert_called_once_with(Bucket="color-analysis")


def test_ensure_bucket_exists_re_raises_non_missing_errors() -> None:
    client = R2Client()
    mock = Mock()
    mock.head_bucket.side_effect = _client_error("403")
    client.client = mock
    client.bucket = "color-analysis"

    with pytest.raises(ClientError):
        client.ensure_bucket_exists()

    mock.create_bucket.assert_not_called()
