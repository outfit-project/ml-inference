import asyncio
import json
from logging import getLogger
from pydantic import ValidationError
from src.domain.errors import PermanentError, TransientError
from src.domain.schemas.messages import ProcessingTaskSchema

logger = getLogger(__name__)


class ItemWorker:
    def __init__(self,consumer,dlq,use_case,max_retries=3,retry_backoff_ms=500):
        self._consumer,self._dlq,self._use_case=consumer,dlq,use_case
        self._max_retries,self._retry_backoff_ms=max_retries,retry_backoff_ms

    async def run(self):
        raw = None
        recovery_required = True
        try:
            while True:
                try:
                    if recovery_required:
                        await self._consumer.recover()
                        recovery_required = False
                    if raw is None: raw = await self._consumer.consume()
                    if raw is None: continue
                    await self.handle(raw)
                    await self._consumer.ack(raw)
                    raw = None
                except asyncio.CancelledError:
                    raise
                except Exception:
                    if raw is None:
                        recovery_required = True
                    logger.exception('Worker operation failed; keeping message for recovery')
                    await asyncio.sleep(2)
        finally:
            await self._consumer.close()
            await self._dlq.close()

    async def handle(self,raw):
        task=self._parse(raw)
        if task is None:
            await self._dlq.push(raw)
            return
        for attempt in range(self._max_retries+1):
            try:
                await self._use_case.set_status(task,'processing')
                await self._use_case.execute(task)
                return
            except PermanentError as exc:
                error = str(exc)
                break
            except TransientError:
                if attempt == self._max_retries:
                    error = 'Photo processing is temporarily unavailable. Please retry.'
                    break
                await asyncio.sleep(self._retry_backoff_ms*(attempt+1)/1000)
            except Exception:
                logger.exception('Unexpected inference failure for item %s',task.item_id)
                error = 'Photo processing failed. Please retry with a clear single-item photo.'
                break
        await self._use_case.set_status(task,'failed',error)
        await self._dlq.push(raw)

    def _parse(self,raw):
        try: return ProcessingTaskSchema.model_validate(json.loads(raw)).to_domain()
        except (ValueError,ValidationError,TypeError): return None
