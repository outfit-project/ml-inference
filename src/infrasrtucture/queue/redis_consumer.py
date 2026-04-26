import redis.asyncio as redis

class RedisConsumer:
    def __init__(
            self,
            queue_name: str,
            redis_url: str,
            timeout: int
    ):
        self._client = redis.from_url(redis_url)
        self._queue = queue_name
        self._timeout = timeout

    async def consume(self) -> bytes | None:
        try:
            result = await self._client.blpop([self._queue], timeout=self._timeout)

            if result:
                return result[1]
            return None
        except redis.RedisError:
            raise