from uuid import UUID

from pydantic import BaseModel


class ItemProcessingTask(BaseModel):
    item_id: UUID
    user_id: UUID
    object_key: str


class ItemEmbeddingResult(BaseModel):
    item_id: UUID
    embedding: list[float]


