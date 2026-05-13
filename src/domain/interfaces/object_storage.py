from typing import Protocol


class IObjectStorage(Protocol):
    async def get_bytes(self, object_key:str) -> tuple[bytes, str]:
        pass
