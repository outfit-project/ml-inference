from logging import getLogger

from src.domain.interfaces.queues import IQueueConsumer, IDeadLetterQueue

logging = getLogger(__name__)

class ItemWorker:
    def __init__(
            self,
            consumer: IQueueConsumer,
            dlq: IDeadLetterQueue,
            use_case: ProccessItemUseCase,
            max_retries: int = 3,
            retry_backoff_ms: int = 500,
    ):