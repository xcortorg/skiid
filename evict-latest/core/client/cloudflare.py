import aioboto3

from typing import Optional, TYPE_CHECKING, BinaryIO, Union
from os import environ
from logging import getLogger
from pathlib import Path

if TYPE_CHECKING:
    from main import Evict

logger = getLogger("evict/cloudflare")


class Cloudflare:
    def __init__(self, bot: "Evict"):
        self.bot = bot
        self._session: Optional[aioboto3.Session] = None
        self._client: Optional[aioboto3.Session.client] = (
            None
        )
        self.bucket_name = environ["CLOUDFLARE_BUCKET_NAME"]
        self.connected = False

    @property
    def credentials(self) -> dict[str, str]:
        return {
            "region_name": "auto",
            "endpoint_url": environ[
                "CLOUDFLARE_ENDPOINT_URL"
            ],
            "aws_access_key_id": environ[
                "CLOUDFLARE_ACCESS_KEY"
            ],
            "aws_secret_access_key": environ[
                "CLOUDFLARE_SECRET_KEY"
            ],
        }

    async def get_client(self):
        if self._client is None:
            self._session = aioboto3.Session()
            self._client = await self._session.client(
                "s3", **self.credentials
            ).__aenter__()
        return self._client

    async def connect(self) -> bool:
        try:
            client = await self.get_client()
            await client.list_objects(
                Bucket=self.bucket_name
            )
            self.connected = True
            logger.info(
                f"Successfully connected to Cloudflare R2 bucket: {self.bucket_name}"
            )
            return True
        except Exception as e:
            self.connected = False
            logger.error(
                f"Failed to connect to Cloudflare R2: {str(e)}"
            )
            return False

    async def close(self):
        if self._client:
            await self._client.__aexit__(None, None, None)
            self._client = None
        if self._session:
            self._session = None
        self.connected = False
        logger.info("Closed Cloudflare R2 connection")

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def upload_file(
        self,
        file_path: Union[str, Path],
        key: str,
        content_type: Optional[str] = None,
    ) -> bool:
        """
        Upload a file to Cloudflare R2 bucket.

        Args:
            file_path: Path to the file to upload
            key: The key (path) where the file will be stored in the bucket
            content_type: Optional content type of the file

        Returns:
            bool: True if upload was successful, False otherwise
        """
        try:
            file_path = (
                Path(file_path)
                if isinstance(file_path, str)
                else file_path
            )
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                return False

            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type

            client = await self.get_client()
            with open(file_path, "rb") as file_data:
                await client.upload_fileobj(
                    file_data,
                    self.bucket_name,
                    key,
                    ExtraArgs=extra_args,
                )
            logger.info(f"uploaded file to R2: {key}")
            return True
        except Exception as e:
            logger.error(
                f"Failed to upload file to R2: {str(e)}"
            )
            return False

    async def upload_fileobj(
        self,
        file_obj: BinaryIO,
        key: str,
        content_type: Optional[str] = None,
    ) -> bool:
        """
        Upload a file-like object to Cloudflare R2 bucket.

        Args:
            file_obj: File-like object to upload
            key: The key (path) where the file will be stored in the bucket
            content_type: Optional content type of the file

        Returns:
            bool: True if upload was successful, False otherwise
        """
        try:
            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type

            client = await self.get_client()
            await client.upload_fileobj(
                file_obj,
                self.bucket_name,
                key,
                ExtraArgs=extra_args,
            )
            logger.info(
                f"Successfully uploaded file object to R2: {key}"
            )
            return True
        except Exception as e:
            logger.error(
                f"Failed to upload file object to R2: {str(e)}"
            )
            return False

    async def delete_file(self, key: str) -> bool:
        """
        Delete a file from Cloudflare R2 bucket.

        Args:
            key: The key (path) of the file to delete in the bucket

        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            client = await self.get_client()
            await client.delete_object(
                Bucket=self.bucket_name, Key=key
            )
            logger.info(
                f"Successfully deleted file from R2: {key}"
            )
            return True
        except Exception as e:
            logger.error(
                f"Failed to delete file from R2: {str(e)}"
            )
            return False
