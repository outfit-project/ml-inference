import torch
from open_clip import create_model_and_transforms
from PIL import Image

from src.domain.interfaces.embedding_model import IEmbeddingModel


class TorchImageEncoder:
    def __init__(
            self,
            model_name:str,
            device:torch.device,
            pretrained:str
    ):
        self._device = device
        model, _, preprocess = create_model_and_transforms(
            model_name=model_name,
            pretrained=pretrained if pretrained else None
        )
        self._model =model.to(self._device)
        self.preprocess = preprocess
        self._model.eval()

    @torch.inference_mode()
    def encode_image(self, image: Image.Image) -> list[float]:
        tensor = self.preprocess(image).unsqueeze(0).to(self._device)
        features = self._model.encode_image(tensor)

        return features.float().squeeze(0).cpu().tolist()


def build_torch_encoder(
        model_name:str,
        pretrained:str,
        device: torch.device
) -> IEmbeddingModel:
    return TorchImageEncoder(model_name, device, pretrained)