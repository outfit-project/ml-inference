from pydantic import BaseModel
import torch


class ModelType(BaseModel):
    backend: str
    embedding_dim: int
    device: torch.device
    torch_model_name: str
    torch_pretrained: str