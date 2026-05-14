from PIL import Image

from src.domain.errors import PermanentError


def guard_image_dim(image:Image.Image, max_pixels: int =10_000_000):
    if image.width * image.height > max_pixels:
        raise PermanentError(
            f"image too large: {image.width}x{image.height} = {image.width * image.height} pixels, "
            f"max allowed: {max_pixels} pixels"
        )