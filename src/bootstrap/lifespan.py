import logging

from src.domain.interfaces.embedding_model import IEmbeddingModel
from src.infrasrtucture.db.embedding_repository import DBEmbeddingRepository
from src.infrasrtucture.queue.redis_consumer import RedisConsumer
from src.infrasrtucture.queue.redis_dlq import RedisDLQ

logger = logging.getLogger(__name__)


_encoder: IEmbeddingModel | None = None
_db_repo: DBEmbeddingRepository | None = None
_consumer: RedisConsumer | None = None
_dlq: RedisDLQ | None = None
_worker: Item