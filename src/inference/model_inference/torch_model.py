import torch
from open_clip import create_model_and_transforms, get_tokenizer
from PIL import Image

from src.inference.model_inference.vocabulary import VocabularyClassifier


class TorchImageEncoder:
    def __init__(self, model_name: str, device: torch.device, pretrained: str):
        self._device = device
        model, _, self.preprocess = create_model_and_transforms(
            model_name=model_name, pretrained=pretrained or None
        )
        self._model = model.to(device).eval()
        self._tokenizer = get_tokenizer(model_name)
        self._classifier = VocabularyClassifier(self._text_features)

    @torch.inference_mode()
    def _text_features(self, prompts):
        features = self._model.encode_text(self._tokenizer(prompts).to(self._device)).float()
        return (features / features.norm(dim=-1, keepdim=True)).cpu().tolist()

    @torch.inference_mode()
    def encode_image(self, image: Image.Image) -> list[float]:
        tensor = self.preprocess(image).unsqueeze(0).to(self._device)
        return self._model.encode_image(tensor).float().squeeze(0).cpu().tolist()

    @torch.inference_mode()
    def classify(self, embedding: list[float]) -> dict:
        return self._classifier.classify(embedding)


def build_torch_encoder(model_name, pretrained, device):
    return TorchImageEncoder(model_name, device, pretrained)
