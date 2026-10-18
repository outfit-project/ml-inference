import io
from PIL import Image, UnidentifiedImageError

from src.domain.errors import ImageDecodeError
from src.inference.preproccess.validate import validate_image_bytes


def decode_image_bytes(data:bytes, max_bytes: int = 10_485_760) ->Image.Image:
    validate_image_bytes(data=data, max_bytes=max_bytes)

    try:
        img = Image.open(io.BytesIO(data))
        if img.width * img.height > 10_000_000:
            raise ImageDecodeError("Image exceeds 10 million pixels")
        img.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as e:
        raise ImageDecodeError("cannot decode image bytes") from e

    if img.mode != "RGB":
        img = img.convert("RGB")

    return img
