import json
from uuid import uuid4
import pytest

from PIL import Image
from src.application.worker.item_worker import ItemWorker
from src.domain.errors import PermanentError
from src.inference.registry.session import InferenceSession
from src.infrasrtucture.queue.redis_consumer import RedisConsumer


def test_inference_returns_full_normalized_metadata_without_confidence():
    class Encoder:
        def encode_image(self,image): return [3.,4.]+[0.]*510
        def classify(self,embedding):
            assert embedding[:2] == pytest.approx([0.6,0.8])
            return {'category':'top','subcategory':'t-shirt','style':'casual','color_hex':'#ff0000'}
    result=InferenceSession(Encoder(),512).analyze(Image.new('RGB',(8,8)))
    assert result['embedding'][:2] == pytest.approx([0.6,0.8])
    assert result['category']=='top' and result['subcategory']=='t-shirt' and result['style']=='casual'
    assert result['color_hex']=='#ff0000' and 'confidence' not in result


@pytest.mark.asyncio
async def test_redis_inflight_recovered_on_worker_restart():
    import fakeredis.aioredis
    redis=fakeredis.aioredis.FakeRedis()
    first=RedisConsumer(queue_name='jobs',redis_url='redis://test',timeout=1); first._client=redis
    await redis.rpush('jobs',b'job-a',b'job-b')
    assert await first.consume()==b'job-a'
    second=RedisConsumer(queue_name='jobs',redis_url='redis://test',timeout=1); second._client=redis
    await second.recover()
    assert await second.consume()==b'job-a'
    await second.ack(b'job-a')
    assert await second.consume()==b'job-b'
    await second.ack(b'job-b')
    assert await redis.llen('jobs:processing')==0


@pytest.mark.asyncio
async def test_permanent_inference_failure_updates_item_before_dead_letter():
    states=[]; dead=[]
    class UseCase:
        async def execute(self,task): raise PermanentError('corrupt image')
        async def set_status(self,task,status,error=None): states.append((status,error))
    class Dead:
        async def push(self,raw): dead.append(raw)
    raw=json.dumps({'event_type':'new_item_uploaded','data':{'item_id':str(uuid4()),'user_id':str(uuid4()),'image_url':'key'}}).encode()
    await ItemWorker(None,Dead(),UseCase(),retry_backoff_ms=0).handle(raw)
    assert states[0][0]=='processing'
    assert states[-1]==('failed','corrupt image')
    assert dead==[raw]


def test_cached_text_features_choose_category_style_color_by_similarity():
    from src.inference.model_inference.vocabulary import VocabularyClassifier
    calls=[]
    def text_features(prompts):
        calls.append(prompts)
        rows=[]
        for prompt in prompts:
            rows.append([1.,0.] if prompt in ('a photo of a t-shirt','a photo of casual style clothing','a photo of a red garment') else [0.,1.])
        return rows
    classifier=VocabularyClassifier(text_features)
    first=classifier.classify([1.,0.])
    second=classifier.classify([1.,0.])
    assert first==second=={'category':'top','subcategory':'t-shirt','style':'casual','color_hex':'#dc2626'}
    assert len(calls)==3


@pytest.mark.asyncio
async def test_processing_callback_has_auth_and_full_ready_payload():
    import httpx
    from src.infrasrtucture.db.embedding_repository import DBEmbeddingRepository
    from src.domain.schemas.items_entities import ItemEmbeddingResult
    requests=[]
    async def handler(request):
        requests.append(request)
        return httpx.Response(200)
    repo=DBEmbeddingRepository('http://wardrobe/items/processing','secret')
    original=httpx.AsyncClient
    def client(*args,**kwargs): return original(*args,transport=httpx.MockTransport(handler),**kwargs)
    from unittest.mock import patch
    with patch('src.infrasrtucture.db.embedding_repository.httpx.AsyncClient',client):
        await repo.save(ItemEmbeddingResult(item_id=uuid4(),embedding=[1.]*512,category='top',subcategory='t-shirt',style='casual',color_hex='#ff0000'))
    assert requests[0].headers['X-Service-Token']=='secret'
    assert json.loads(requests[0].content)['processing_status']=='ready'
    assert json.loads(requests[0].content)['subcategory']=='t-shirt'

@pytest.mark.asyncio
@pytest.mark.parametrize('vanished_at', ['processing', 'ready', 'failed'])
async def test_deleted_item_callbacks_do_not_block_next_task(monkeypatch, vanished_at):
    import asyncio
    import io
    import httpx
    import fakeredis.aioredis
    from src.application.use_cases.item_process import ProcessItemUseCase
    from src.infrasrtucture.db.embedding_repository import DBEmbeddingRepository

    first_id, second_id, owner = uuid4(), uuid4(), uuid4()
    image = io.BytesIO()
    Image.new('RGB', (8, 8), 'red').save(image, format='PNG')
    callbacks, dead = [], []

    class Storage:
        async def get_bytes(self, key):
            if key == 'first' and vanished_at == 'failed':
                raise PermanentError('Stored photo vanished')
            return image.getvalue(), 'image/png'

    class Session:
        def analyze(self, image):
            return dict(embedding=[1.] * 512, category='top', subcategory='t-shirt',
                        style='casual', color_hex='#ff0000')

    class Dead:
        async def push(self, raw): dead.append(raw)
        async def close(self): pass

    async def handler(request):
        payload = json.loads(request.content)
        callbacks.append(payload)
        if payload['item_id'] == str(first_id):
            if vanished_at == 'processing' or payload['processing_status'] == vanished_at:
                return httpx.Response(404)
        return httpx.Response(200)

    original_client = httpx.AsyncClient
    monkeypatch.setattr('src.infrasrtucture.db.embedding_repository.httpx.AsyncClient',
                        lambda **kwargs: original_client(transport=httpx.MockTransport(handler), **kwargs))
    redis = fakeredis.aioredis.FakeRedis()
    class FiniteConsumer(RedisConsumer):
        reads = 0
        async def consume(self):
            if self.reads == 2:
                raise asyncio.CancelledError
            self.reads += 1
            return await super().consume()
        async def close(self): pass

    consumer = FiniteConsumer(queue_name='deleted-jobs', redis_url='redis://test', timeout=1)
    consumer._client = redis
    messages = [json.dumps({'event_type': 'new_item_uploaded', 'data': {
        'item_id': str(item_id), 'user_id': str(owner), 'image_url': key,
    }}).encode() for item_id, key in ((first_id, 'first'), (second_id, 'second'))]
    await redis.rpush('deleted-jobs', *messages)
    repository = DBEmbeddingRepository('http://wardrobe/items/processing', 'secret')
    use_case = ProcessItemUseCase(Storage(), repository, Session())
    worker = asyncio.create_task(ItemWorker(consumer, Dead(), use_case, retry_backoff_ms=0).run())

    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(worker, timeout=3)
    assert any(p['item_id'] == str(second_id) and p['processing_status'] == 'ready' for p in callbacks)
    assert await redis.llen('deleted-jobs:processing') == 0
    assert await redis.llen('deleted-jobs') == 0
    assert len(dead) == (1 if vanished_at == 'failed' else 0)
    await redis.aclose()

@pytest.mark.asyncio
async def test_lost_blmove_response_recovers_item_without_restart():
    import asyncio
    import fakeredis.aioredis
    redis = fakeredis.aioredis.FakeRedis()
    completed = []
    first_id, second_id, owner = uuid4(), uuid4(), uuid4()

    class AmbiguousConsumer(RedisConsumer):
        reads = 0
        async def consume(self):
            if self.reads >= 2 and await self._client.llen(self._queue) == 0:
                raise asyncio.CancelledError
            raw = await super().consume()
            self.reads += 1
            if self.reads == 1:
                raise ConnectionError('BLMOVE completed but its response was lost')
            return raw
        async def close(self): pass

    class UseCase:
        async def set_status(self, task, status, error=None): pass
        async def execute(self, task): completed.append(task.item_id)

    class Dead:
        async def push(self, raw): pytest.fail('Valid tasks must not be dead-lettered')
        async def close(self): pass

    consumer = AmbiguousConsumer(queue_name='lost-response', redis_url='redis://test', timeout=1)
    consumer._client = redis
    messages = [json.dumps({'event_type': 'new_item_uploaded', 'data': {
        'item_id':str(item_id), 'user_id':str(owner), 'image_url':'photo',
    }}).encode() for item_id in (first_id, second_id)]
    await redis.rpush('lost-response', *messages)
    worker = ItemWorker(consumer, Dead(), UseCase())
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(worker.run(), timeout=10)
    assert completed == [first_id, second_id]
    assert await redis.llen('lost-response:processing') == 0
    assert await redis.llen('lost-response') == 0
    await redis.aclose()
