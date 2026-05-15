import asyncio
import json
from logging import getLogger

from pydantic import ValidationError

from src.application.use_cases.item_process import ProcessItemUseCase
from src.domain.errors import PermanentError, TransientError
from src.domain.interfaces.queues import IQueueConsumer, IDeadLetterQueue
from src.domain.schemas.messages import ProcessingTaskSchema

logger = getLogger(__name__)


class ItemWorker:
    def __init__(
            self,
            consumer: IQueueConsumer,
            dlq: IDeadLetterQueue,
            use_case: ProcessItemUseCase,
            max_retries: int = 3,
            retry_backoff_ms: int = 500,
    ):
        self._consumer = consumer
        self._dlq = dlq
        self._use_case = use_case
        self._max_retries = max_retries
        self._retry_backoff_ms = retry_backoff_ms

    async def run(self) -> None:
        logger.info("Worker started, queue consumer listening")
        while True:
            raw = await self._consumer.consume()
            if raw is None:
                continue
            try:
                await self.handle(raw)
            except Exception:
                logger.exception("Unhandled worker error, message sent to DLQ")
                await self._dlq.push(raw)

    async def handle(self, raw: bytes) -> None:
        task = self._parse(raw)
        if task is None:
            await self._dlq.push(raw)
            return

        logger.info("Processing item_id=%s object_key=%s", task.item_id, task.object_key)
        retries = 0
        while True:
            try:
                await self._use_case.execute(task)
                logger.info("Finished item_id=%s", task.item_id)
                return
            except PermanentError as e:
                logger.error("Permanent error for item %s: %s", task.item_id, e)
                await self._dlq.push(raw)
                return
            except TransientError as e:
                retries += 1
                if retries > self._max_retries:
                    logger.error(
                        "Max retries exceeded for item %s: %s",
                        task.item_id,
                        e,
                    )
                    await self._dlq.push(raw)
                    return
                wait = self._retry_backoff_ms * retries / 1000
                logger.warning(
                    "Transient error, retry %d/%d in %.1fs: %s",
                    retries,
                    self._max_retries,
                    wait,
                    e,
                )
                await asyncio.sleep(wait)

    def _parse(self, raw: bytes):
        try:
            payload = json.loads(raw)
            return ProcessingTaskSchema.model_validate(payload).to_domain()
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error("Invalid message payload, sending to DLQ: %s", e)
            return None
