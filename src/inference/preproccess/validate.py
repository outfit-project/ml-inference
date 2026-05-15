from src.domain.errors import ImageDecodeError


def validate_image_bytes(data: bytes, max_bytes: int = 10_485_760):
    if not data:
        raise ImageDecodeError("invalid image data")

    if len(data) > max_bytes:
        raise ImageDecodeError("image too large")

