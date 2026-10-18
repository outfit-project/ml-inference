from typing import runtime_checkable, Protocol


@runtime_checkable
class IQueueConsumer(Protocol):
    async def consume(self) -> bytes | None:
        pass

    async def recover(self) -> None:
        pass

    async def ack(self, raw: bytes) -> None:
        pass

    async def close(self) -> None:
        pass


@runtime_checkable
class IDeadLetterQueue(Protocol):
    async def push(self, raw_message: bytes) -> None:
        pass

    async def close(self) -> None:
        pass
