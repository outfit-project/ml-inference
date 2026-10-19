from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import uuid4

from botocore.exceptions import ClientError, EndpointConnectionError
import httpx
import pytest

from src.domain.errors import PermanentError, TransientError
from src.domain.schemas.items_entities import ItemEmbeddingResult
from src.infrasrtucture.db.embedding_repository import DBEmbeddingRepository
from src.infrasrtucture.storage.object_fetcher import ObjectFetcher


def ready_result():
    return ItemEmbeddingResult(
        item_id=uuid4(), embedding=[1.0] * 512, category='top',
        subcategory='t-shirt', style='casual', color_hex='#ff0000',
    )


@pytest.mark.asyncio
@pytest.mark.parametrize('operation,status,error_type', [
    ('save', 401, PermanentError),
    ('save', 422, PermanentError),
    ('save', 503, TransientError),
    ('set_status', 401, TransientError),
    ('set_status', 422, TransientError),
    ('set_status', 503, TransientError),
])
async def test_callback_adapter_classifies_errors_for_worker_retries(monkeypatch, operation, status, error_type):
    def handler(request):
        return httpx.Response(status)

    original_client = httpx.AsyncClient
    monkeypatch.setattr(
        'src.infrasrtucture.db.embedding_repository.httpx.AsyncClient',
        lambda **kwargs: original_client(transport=httpx.MockTransport(handler), **kwargs),
    )
    repository = DBEmbeddingRepository('http://wardrobe/items/processing', 'service-token')
    with pytest.raises(error_type):
        if operation == 'save':
            await repository.save(ready_result())
        else:
            await repository.set_status(uuid4(), 'processing')


@pytest.mark.asyncio
@pytest.mark.parametrize('operation', ['save', 'set_status'])
async def test_callback_connection_failure_remains_retryable(monkeypatch, operation):
    def handler(request):
        raise httpx.ConnectError('connection unavailable', request=request)

    original_client = httpx.AsyncClient
    monkeypatch.setattr(
        'src.infrasrtucture.db.embedding_repository.httpx.AsyncClient',
        lambda **kwargs: original_client(transport=httpx.MockTransport(handler), **kwargs),
    )
    repository = DBEmbeddingRepository('http://wardrobe/items/processing', 'service-token')
    with pytest.raises(TransientError):
        if operation == 'save':
            await repository.save(ready_result())
        else:
            await repository.set_status(uuid4(), 'failed', 'bad image')


@pytest.mark.asyncio
@pytest.mark.parametrize('code,error_type', [
    ('NoSuchKey', PermanentError),
    ('NoSuchBucket', PermanentError),
    ('404', PermanentError),
    ('AccessDenied', TransientError),
])
async def test_storage_adapter_distinguishes_missing_photo_from_service_failure(code, error_type):
    class S3:
        async def get_object(self, *, Bucket, Key):
            assert Bucket == 'photos' and Key == 'users/shirt.png'
            raise ClientError({'Error': {'Code': code, 'Message': 'storage error'}}, 'GetObject')

    @asynccontextmanager
    async def client(*args, **kwargs):
        yield S3()

    storage = ObjectFetcher('http://storage', 'access', 'secret', 'photos')
    storage._session = SimpleNamespace(client=client)
    with pytest.raises(error_type):
        await storage.get_bytes('/users/shirt.png')


@pytest.mark.asyncio
async def test_storage_connection_failure_remains_retryable():
    @asynccontextmanager
    async def client(*args, **kwargs):
        raise EndpointConnectionError(endpoint_url='http://storage')
        yield

    storage = ObjectFetcher('http://storage', 'access', 'secret', 'photos')
    storage._session = SimpleNamespace(client=client)
    with pytest.raises(TransientError):
        await storage.get_bytes('users/shirt.png')
