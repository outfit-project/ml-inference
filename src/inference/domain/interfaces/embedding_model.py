from typing import Protocol, runtime_checkable

from PIL import Image


@runtime_checkable
class IEmbeddingModel(Protocol):
    def encode_image(self, image: Image.Image) -> list[float]:
        pass

