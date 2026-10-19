import aioboto3
from botocore.exceptions import BotoCoreError, ClientError

from src.domain.errors import PermanentError, TransientError

class ObjectFetcher:
    def __init__(
            self,
            endpoint_url: str,
            access_key:str,
            secret_key:str,
            bucket_name:str
    ):
        self._endpoint = endpoint_url
        self._access = access_key
        self._secret = secret_key
        self._bucket = bucket_name
        self._session = aioboto3.Session()

    async def get_bytes(self, object_key:str) -> tuple[bytes, str]:
        clear_object = object_key.lstrip('/')
        try:
            async with self._session.client(
                "s3",
                endpoint_url=self._endpoint,
                aws_access_key_id=self._access,
                aws_secret_access_key=self._secret,
            ) as s3:
                response = await s3.get_object(Bucket=self._bucket, Key=clear_object)
                data = await response["Body"].read()
                content_type = response.get("ContentType", "application/octet-stream")
                return data, content_type
        except ClientError as exc:
            code = exc.response.get('Error', {}).get('Code', '')
            if code in ('NoSuchKey', '404', 'NoSuchBucket'):
                raise PermanentError('The stored photo could not be found. Please upload it again.') from exc
            raise TransientError(f'Storage error: {exc}') from exc
        except BotoCoreError as exc:
            raise TransientError(f'Storage error: {exc}') from exc


