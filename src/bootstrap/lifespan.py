import logging

from src.application.use_cases.item_process import ProcessItemUseCase
from src.application.worker.item_worker import ItemWorker
from src.config.settings import Settings, settings
from src.domain.interfaces.embedding_model import IEmbeddingModel
from src.domain.schemas.model_type import ModelType
from src.inference.registry.registry import build_model
from src.inference.registry.session import InferenceSession
from src.infrasrtucture.db.embedding_repository import DBEmbeddingRepository
from src.infrasrtucture.queue.redis_consumer import RedisConsumer
from src.infrasrtucture.queue.redis_dlq import RedisDLQ
from src.infrasrtucture.storage.object_fetcher import ObjectFetcher

logger = logging.getLogger(__name__)


_encoder: IEmbeddingModel | None = None
_db_repo: DBEmbeddingRepository | None = None
_consumer: RedisConsumer | None = None
_dlq: RedisDLQ | None = None
_worker: ItemWorker | None = None

def get_embedding_model() -> IEmbeddingModel:
    if _encoder is None:
        raise RuntimeError("Embedding model is not initialized")
    return _encoder


def get_worker() -> ItemWorker:
    if _worker is None:
        raise RuntimeError("Worker model is not initialized")
    return _worker

def startup_embedding_model(cfg:Settings | None = None) -> IEmbeddingModel | None:
    global _encoder
    cfg = cfg or settings

    if not cfg.MODEL_LOAD_ON_STARTUP:
        _encoder = None

        return None
    spec = ModelType(
        backend="clip",
        embedding_dim=cfg.EMBEDDING_DIM,
        device=cfg.INFERENCE_DEVICE,
        openclip_model_name=cfg.OPENCLIP_MODEL_NAME,
        openclip_pretrained=cfg.OPENCLIP_PRETRAINED,
    )

    _encoder = build_model(spec)

    logger.info(f"Created embedding model: {spec}")

    return _encoder


async def startup_worker(cfg: Settings | None = None) -> ItemWorker:
    global _db_repo, _consumer, _dlq, _worker
    cfg = cfg or settings

    encoder = get_embedding_model()
    session = InferenceSession(encoder=encoder, expected_dim=cfg.EMBEDDING_DIM)

    _db_repo = DBEmbeddingRepository(cfg.WARDROBE_EMBEDDING_URL)
    logger.info("Wardrobe embedding API: %s", cfg.WARDROBE_EMBEDDING_URL)

    object_store = ObjectFetcher(
        endpoint_url=cfg.MINIO_ENDPOINT or "",
        access_key=cfg.MINIO_ACCESS_KEY or "",
        secret_key=cfg.MINIO_SECRET_KEY or "",
        bucket_name=cfg.MINIO_BUCKET or "",
    )

    _consumer = RedisConsumer(
        redis_url=cfg.REDIS_URL,
        queue_name=cfg.ML_TASKS_QUEUE,
        timeout=cfg.REDIS_BLPOP_TIMEOUT_SEC,
    )
    _dlq = RedisDLQ(
        redis_url=cfg.REDIS_URL,
        dlq_name=cfg.ML_TASKS_DLQ,
    )

    use_case = ProcessItemUseCase(
        object_storage=object_store,
        embedding_repo=_db_repo,
        session=session,
        settings=cfg,
    )

    _worker = ItemWorker(
        consumer=_consumer,
        dlq=_dlq,
        use_case=use_case,
        max_retries=cfg.WORKER_MAX_RETRIES,
        retry_backoff_ms=cfg.WORKER_RETRY_BACKOFF_MS,
    )
    logger.info("Worker initialized")
    return _worker


def shutdown_embedding_model() -> None:
    global _encoder
    _encoder = None

