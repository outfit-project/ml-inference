import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    ENV: str = os.getenv("ENV", "dev").strip().lower()

    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
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

    OPENCLIP_MODEL_NAME: str = os.getenv("OPENCLIP_MODEL_NAME", "ViT-B-32")
    OPENCLIP_PRETRAINED: str = os.getenv("OPENCLIP_PRETRAINED", "openai")




settings = Settings()

REDIS_URL = settings.REDIS_URL
ML_TASKS_QUEUE = settings.ML_TASKS_QUEUE
ML_TASKS_DLQ = settings.ML_TASKS_DLQ
