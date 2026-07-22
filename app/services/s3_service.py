from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError

from app.config import settings
from app.config.logging import logger


class S3Service:
    def __init__(self):
        self.client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY,
            aws_secret_access_key=settings.AWS_SECRET_KEY,
            region_name=settings.AWS_REGION,
        )
        self.bucket = settings.AWS_BUCKET_NAME

    def download_file(self, resume_file_url: str) -> bytes:
        key = self._extract_key(resume_file_url)
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read()
        except ClientError as e:
            logger.error(f"[s3] failed to download {key}: {e}")
            raise

    @staticmethod
    def _extract_key(resume_file_url: str) -> str:
        if resume_file_url.startswith("http"):
            return urlparse(resume_file_url).path.lstrip("/")
        return resume_file_url