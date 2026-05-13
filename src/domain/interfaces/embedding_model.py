from typing import Protocol, runtime_checkable

from PIL import Image

from src.domain.schemas.items_entities import ItemEmbeddingResult


@runtime_checkable
class IEmbeddingModel(Protocol):
    def encode_image(self, image: Image.Image) -> list[float]:
        pass


@runtime_checkable
class EmbeddingRepository(Protocol):
    async def save(self, result: ItemEmbeddingResult):
        pass