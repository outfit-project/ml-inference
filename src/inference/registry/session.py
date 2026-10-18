import math
from PIL import Image

from src.domain.errors import EmbeddingDimensionError, PermanentError
from src.inference.postproccess.normalize import normalize_func


class InferenceSession:
    def __init__(self, encoder, expected_dim: int | None = None):
        self._encoder = encoder
        self._expected = expected_dim

    def get_embedding(self, image: Image.Image) -> list[float]:
        raw = self._encoder.encode_image(image)
        if self._expected is not None and len(raw) != self._expected:
            raise EmbeddingDimensionError(self._expected, len(raw))
        if not raw or not all(math.isfinite(x) for x in raw) or not any(raw):
            raise PermanentError('Model returned an invalid embedding')
        return normalize_func(raw)

    def analyze(self, image: Image.Image) -> dict:
        embedding = self.get_embedding(image)
        return {'embedding': embedding, **self._encoder.classify(embedding)}
