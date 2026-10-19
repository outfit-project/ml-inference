import asyncio
from functools import partial
from src.domain.interfaces.object_storage import IObjectStorage
from src.domain.interfaces.processing_repository import IProcessingRepository
from src.domain.schemas.items_entities import ItemEmbeddingResult, ItemProcessingTask
from src.inference.preproccess.decode import decode_image_bytes
from src.inference.preproccess.guard_image import guard_image_dim
from src.inference.preproccess.validate import validate_image_bytes
from src.inference.registry.session import InferenceSession


class ProcessItemUseCase:
    def __init__(
            self,
            object_storage: IObjectStorage,
            embedding_repo: IProcessingRepository,
            session: InferenceSession,
    ) -> None:
        self._storage = object_storage
        self._embedding_repo = embedding_repo
        self._session = session

    async def execute(self, task: ItemProcessingTask) -> None:
        image_bytes, _ = await self._storage.get_bytes(task.object_key)

        validate_image_bytes(image_bytes)
        image = decode_image_bytes(image_bytes)
        guard_image_dim(image, 10_000_000)

        loop = asyncio.get_running_loop()
        analysis = await loop.run_in_executor(
            None,
            partial(self._session.analyze, image),
        )

        await self._embedding_repo.save(
            ItemEmbeddingResult(item_id=task.item_id, **analysis)
        )


    async def set_status(self, task: ItemProcessingTask, status: str, error: str | None = None) -> None:
        await self._embedding_repo.set_status(task.item_id, status, error)
