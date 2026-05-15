import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _parse_bool(raw: str | None, default: bool) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _parse_positive_int(name: str, default: int, minimum: int = 1) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        value = default
    else:
        value = int(raw)
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}, got {value}")
    return value


@dataclass
class Settings:
    ENV: str = os.getenv("ENV", "dev").strip().lower()

    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:16379/0")
    ML_TASKS_QUEUE: str = os.getenv("ML_TASKS_QUEUE", "ml_tasks")
    ML_TASKS_DLQ: str = os.getenv("ML_TASKS_DLQ", "ml_tasks_dlq")

    MINIO_ENDPOINT: str | None = os.getenv("MINIO_ENDPOINT")
    MINIO_ACCESS_KEY: str | None = os.getenv("MINIO_ACCESS_KEY")
    MINIO_SECRET_KEY: str | None = os.getenv("MINIO_SECRET_KEY")
    MINIO_BUCKET: str | None = os.getenv("MINIO_BUCKET")

    INFERENCE_DEVICE: str = (os.getenv("INFERENCE_DEVICE", "cpu") or "cpu").strip().lower()
    MODEL_ARTIFACTS_DIR: str = os.getenv("MODEL_ARTIFACTS_DIR") or "./artifacts/models"
    MODEL_NAME: str = os.getenv("MODEL_NAME") or "clip"
    MODEL_VERSION: str = os.getenv("MODEL_VERSION") or "1"
    MODEL_LOAD_ON_STARTUP: bool = field(
        default_factory=lambda: _parse_bool(os.getenv("MODEL_LOAD_ON_STARTUP"), True)
    )

    REDIS_BLPOP_TIMEOUT_SEC: int = field(
        default_factory=lambda: _parse_positive_int("REDIS_BLPOP_TIMEOUT_SEC", 5, minimum=1)
    )

    OPENCLIP_MODEL_NAME: str = os.getenv("OPENCLIP_MODEL_NAME", "ViT-B-32")
    OPENCLIP_PRETRAINED: str = os.getenv("OPENCLIP_PRETRAINED", "openai")

    EMBEDDING_DIM: int = field(
        default_factory=lambda: _parse_positive_int("EMBEDDING_DIM", 512, minimum=1)
    )

    WARDROBE_EMBEDDING_URL: str = (
        os.getenv("WARDROBE_EMBEDDING_URL", "http://localhost:8002/items/embedding")
        or "http://localhost:8002/items/embedding"
    ).strip()

    WORKER_MAX_RETRIES: int = field(
        default_factory=lambda: _parse_positive_int("WORKER_MAX_RETRIES", 3, minimum=1)
    )
    WORKER_RETRY_BACKOFF_MS: int = field(
        default_factory=lambda: _parse_positive_int(
            "WORKER_RETRY_BACKOFF_MS", 500, minimum=0
        )
    )


settings = Settings()

REDIS_URL = settings.REDIS_URL
ML_TASKS_QUEUE = settings.ML_TASKS_QUEUE
ML_TASKS_DLQ = settings.ML_TASKS_DLQ
