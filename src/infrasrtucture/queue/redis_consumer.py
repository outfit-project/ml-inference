import redis.asyncio as redis

from src.domain.errors import TaskPayloadError


class RedisConsumer:
    def __init__(
            self,
            queue_name: str,
            redis_url: str,
            timeout: int,
    ):
        self._client = redis.from_url(redis_url, decode_responses=False)
        self._queue = queue_name
        self._timeout = timeout

    async def consume(self) -> bytes | None:
        try:
            result = await self._client.blpop([self._queue], timeout=self._timeout)
            if not result:
                return None
            raw = result[1]
            if isinstance(raw, str):
                return raw.encode("utf-8")
            return raw
        except redis.RedisError as e:
            raise TaskPayloadError(
                f"Error reading from Redis queue {self._queue}: {e}"
            ) from e

    async def close(self) -> None:
        await self._client.aclose()
