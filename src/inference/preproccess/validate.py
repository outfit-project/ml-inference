def validate_image_bytes(data: bytes, max_bytes: int = 1_048_576):
    if not data:
        raise ImageDe