from typing import Optional
from aiobotocore.session import AioSession

from modules import config

class S3Handler:
    def __init__(self):
        self.session = AioSession()
        self.endpoint_url = config.CLOUDFLARE.R2_ENDPOINT_URL
        self.aws_access_key_id = config.CLOUDFLARE.R2_ACCESS_KEY_ID
        self.aws_secret_access_key = config.CLOUDFLARE.R2_SECRET_ACCESS_KEY

    async def upload_file(self, bucket_name: str, file_data: bytes, file_name: str, content_type: str, file_directory: Optional[str] = None) -> dict:
        key = f"{file_directory}/{file_name}" if file_directory else file_name
        async with self.session.create_client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
        ) as client:
            try:
                res = await client.put_object(Bucket=bucket_name, Key=key, Body=file_data, ContentType=content_type)
                return {"success": True, "response": res}
            except Exception as e:
                return {"success": False, "error": str(e)}

    async def delete_file(self, bucket_name: str, file_name: str, file_directory: Optional[str] = None) -> dict:
        key = f"{file_directory}/{file_name}" if file_directory else file_name
        async with self.session.create_client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
        ) as client:
            try:
                res = await client.delete_object(Bucket=bucket_name, Key=key)
                return {"success": True, "response": res}
            except Exception as e:
                return {"success": False, "error": str(e)}

    async def file_exists(self, bucket_name: str, file_name: str, file_directory: Optional[str] = None) -> bool:
        key = f"{file_directory}/{file_name}" if file_directory else file_name
        async with self.session.create_client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
        ) as client:
            try:
                await client.head_object(Bucket=bucket_name, Key=key)
                return True
            except client.exceptions.ClientError:
                return False