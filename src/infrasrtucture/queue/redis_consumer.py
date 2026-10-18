import redis.asyncio as redis


class RedisConsumer:
    """Single-worker reliable FIFO: acknowledge only after the callback is stored."""
    def __init__(self, queue_name: str, redis_url: str, timeout: int):
        self._client = redis.from_url(redis_url, decode_responses=False)
        self._queue = queue_name
        self._processing = queue_name + ':processing'
        self._timeout = timeout

    async def recover(self):
        while await self._client.rpoplpush(self._processing, self._queue) is not None:
            pass

    async def consume(self) -> bytes | None:
        return await self._client.blmove(self._queue,self._processing,self._timeout,src='LEFT',dest='RIGHT')

    async def ack(self, raw: bytes):
        await self._client.lrem(self._processing,1,raw)

    async def close(self):
        await self._client.aclose()
