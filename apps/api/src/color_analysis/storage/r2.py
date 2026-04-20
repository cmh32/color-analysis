from typing import Any

import boto3

from color_analysis.config import get_settings


class R2Client:
    def __init__(self) -> None:
        settings = get_settings()
        self.bucket = settings.s3_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
        )

    def put_presigned_post(self, key: str, expires_in_seconds: int = 300) -> dict[str, Any]:
        return self.client.generate_presigned_post(
            Bucket=self.bucket,
            Key=key,
            ExpiresIn=expires_in_seconds,
        )

    def get_object_bytes(self, key: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        body = response["Body"].read()
        if not isinstance(body, bytes):
            raise TypeError("Expected bytes body from S3")
        return body

    def put_object_bytes(self, key: str, payload: bytes, content_type: str = "application/octet-stream") -> None:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=payload, ContentType=content_type)

    def delete_object(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def list_by_session_prefix(self, session_id: str) -> list[str]:
        prefix = f"sessions/{session_id}/"
        response = self.client.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
        contents = response.get("Contents", [])
        return [item["Key"] for item in contents if "Key" in item]
