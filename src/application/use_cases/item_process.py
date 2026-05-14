from src.config.settings import Settings
from src.domain.interfaces.embedding_model import IEmbeddingModel, IEmbeddingRepository
from src.domain.interfaces.object_storage import IObjectStorage
from src.domain.schemas.items_entities import ItemProcessingTask, ItemEmbeddingResult
from src.inference.preproccess.decode import decode_image_bytes
from src.inference.preproccess.guard_image import guard_image_dim
from src.inference.preproccess.validate import validate_image_bytes
from src.inference.registry.session import InferenceSession


class ProcessItemUseCase:
    def __init__(
            self,
            object_storage: IObjectStorage,
            embedding_repo: IEmbeddingRepository,
            session: InferenceSession,
            settings: Settings,
    ) -> None:
        self._storage = object_storage
        self._embedding_repo = embedding_repo
        self._session = session
        self.settings = settings

    async def execute(self, task:ItemProcessingTask)->None:
        image_bytes, _ = await self._storage.get_bytes(task.object_key)

        validate_image_bytes(image_bytes)

        image = decode_image_bytes(image_bytes)

        guard_image_dim(image, 10_000_000)

        embedding = self._session.get_embedding(image)

        await self._embedding_repo.save(
            ItemEmbeddingResult(item_id=task.item_id, embedding=embedding)
        )