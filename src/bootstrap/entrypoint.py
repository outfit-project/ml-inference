import asyncio
import logging
import signal
import sys
import time

from src.bootstrap.lifespan import startup_embedding_model, startup_worker, get_worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    startup_embedding_model()
    await startup_worker()

    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()

    for sign in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sign, stop_event.set)

    worker_task = asyncio.create_task(get_worker().run())
    stop_task = asyncio.create_task(stop_event.wait())


    done, pending = await asyncio.wait(
        [worker_task, stop_task],
        return_when=asyncio.FIRST_COMPLETED,
    )
    for task in pending:
        task.cancel()
    for task in done:
        if task is worker_task and not task.cancelled():
            exc = task.exception()
            if exc is not None:
                logger.exception("Worker stopped with error", exc_info=exc)
                raise exc


if __name__ == "__main__":
    asyncio.run(main())