from uuid import UUID
from typing import Literal
from pydantic import BaseModel, FiniteFloat, Field


class ItemProcessingTask(BaseModel):
    item_id: UUID
    user_id: UUID
    object_key: str


class ItemEmbeddingResult(BaseModel):
    item_id: UUID
    processing_status: Literal['ready'] = 'ready'
    embedding: list[FiniteFloat] = Field(min_length=512,max_length=512)
    category: str
    subcategory: str
    style: str
    color_hex: str
