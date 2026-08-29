import asyncio
import socket
from urllib.parse import urlparse

import boto3
from botocore.config import Config
from app.config import get_settings


class StorageUnavailable(Exception):
    pass


def _endpoint_reachable(endpoint: str, timeout: float = 0.5) -> bool:
    parsed = urlparse(endpoint)
    host = parsed.hostname or "localhost"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    candidates = []
    if host in ("localhost",):
        candidates = ["127.0.0.1", host]
    else:
        candidates = [host]
    for candidate in candidates:
        try:
            with socket.create_connection((candidate, port), timeout=timeout):
                return True
        except OSError:
            continue
    return False


class ObjectStorage:
    def __init__(self):
        s = get_settings()
        self.bucket = s.storage_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=s.storage_endpoint,
            aws_access_key_id=s.storage_access_key,
            aws_secret_access_key=s.storage_secret_key,
            config=Config(connect_timeout=1, read_timeout=3, retries={"max_attempts": 1}),
        )

    async def ensure_bucket(self):
        def ensure():
            try:
                self.client.head_bucket(Bucket=self.bucket)
            except Exception:
                self.client.create_bucket(Bucket=self.bucket)

        await asyncio.to_thread(ensure)

    async def put(self, key: str, content: bytes, content_type: str):
        if not get_settings().storage_enabled:
            raise StorageUnavailable("storage desativado")
        if not _endpoint_reachable(get_settings().storage_endpoint):
            raise StorageUnavailable("endpoint de storage inacessível")
        await self.ensure_bucket()
        await asyncio.to_thread(
            self.client.put_object,
            Bucket=self.bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
        )