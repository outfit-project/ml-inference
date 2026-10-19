from typing import Protocol
from uuid import UUID

from src.domain.schemas.items_entities import ItemEmbeddingResult


class IProcessingRepository(Protocol):
    async def save(self, result: ItemEmbeddingResult) -> None: ...

    async def set_status(self, item_id: UUID, status: str, error: str | None = None) -> None: ...
