import redis.asyncio as redis

from src.domain.errors import TransientError


class RedisDLQ:
    def __init__(
            self,
            redis_url: str,
            dlq_name: str
    ):
        self._client = redis.from_url(redis_url)
        self._name = dlq_name

    async def push(self, raw_message: bytes) -> bytes | None:
        try:
            await self._client.rpush(self._name, raw_message)

        except Exception:
            raise TransientError(f"DLQ write error {self._name}")


    async def close(self) -> None:
        await self._client.aclose()