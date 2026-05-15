import torch

from src.domain.errors import PermanentError
from src.domain.interfaces.embedding_model import IEmbeddingModel
from src.domain.schemas.model_type import ModelType
from src.inference.model_inference.torch_model import build_torch_encoder


def build_model(spec: ModelType) -> IEmbeddingModel:
    if spec.backend != "clip":
        raise PermanentError(
            f"Backend {spec.backend!r} is unknown. Allowed backends: 'clip'."
        )
    return build_torch_encoder(
        model_name=spec.openclip_model_name,
        pretrained=spec.openclip_pretrained,
        device=torch.device(spec.device),
    )
