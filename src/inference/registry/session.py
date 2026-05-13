from PIL import Image

from src.domain.errors import EmbeddingDimensionError
from src.domain.interfaces.embedding_model import IEmbeddingModel
from src.inference.postproccess.copy_embedding import quantize_embedding
from src.inference.postproccess.normalize import normalize_func


class InferenceSession:
    def __init__(
            self,
            encoder: IEmbeddingModel,
            expected_dim: int | None = None,
    ):
        self._encoder = encoder
        self._expected = expected_dim

    def get_embedding(self, image: Image.Image) -> list[float]:
        raw_vector = self._encoder.encode_image(image)

        if self._expected is not None and len(raw_vector) != self._expected:
            raise EmbeddingDimensionError(
                self._expected,
                len(raw_vector),
            )

        normalize_vector = normalize_func(raw_vector)
        final_vector = quantize_embedding(normalize_vector)

        return final_vector
