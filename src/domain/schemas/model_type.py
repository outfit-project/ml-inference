from pydantic import BaseModel, ConfigDict, Field


class ModelType(BaseModel):
    model_config = ConfigDict(frozen=True)

    backend: str
    embedding_dim: int = Field(ge=1)
    device: str = Field(
        ...,
        description="cpu, cuda, cuda:0, mps, … — передаётся в torch.device()",
    )
    openclip_model_name: str
    openclip_pretrained: str
