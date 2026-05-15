import asyncio
from functools import partial
import httpx
from botocore.exceptions import BotoCoreError, ClientError
from src.config.settings import Settings
from src.domain.errors import PermanentError, TransientError
from src.domain.interfaces.object_storage import IObjectStorage
from src.domain.schemas.items_entities import ItemEmbeddingResult, ItemProcessingTask
from src.inference.preproccess.decode import decode_image_bytes
from src.inference.preproccess.guard_image import guard_image_dim
from src.inference.preproccess.validate import validate_image_bytes
from src.inference.registry.session import InferenceSession


class ProcessItemUseCase:
    def __init__(
            self,
            object_storage: IObjectStorage,
            embedding_repo,
            session: InferenceSession,
            settings: Settings,
    ) -> None:
        self._storage = object_storage
        self._embedding_repo = embedding_repo
        self._session = session
        self.settings = settings

    async def execute(self, task: ItemProcessingTask) -> None:
        try:
            image_bytes, _ = await self._storage.get_bytes(task.object_key)
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("NoSuchKey", "404", "NoSuchBucket"):
                raise PermanentError(f"Object not found: {task.object_key}") from e
            raise TransientError(f"Storage error: {e}") from e
        except BotoCoreError as e:
            raise TransientError(f"Storage error: {e}") from e

        validate_image_bytes(image_bytes)
        image = decode_image_bytes(image_bytes)
        guard_image_dim(image, 10_000_000)

        loop = asyncio.get_running_loop()
        embedding = await loop.run_in_executor(
            None,
            partial(self._session.get_embedding, image),
        )

        try:
            await self._embedding_repo.save(
                ItemEmbeddingResult(item_id=task.item_id, embedding=embedding)
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code >= 500:
                raise TransientError(f"Wardrobe API error: {e}") from e
            raise PermanentError(f"Wardrobe API error: {e}") from e
        except httpx.HTTPError as e:
            raise TransientError(f"Wardrobe API error: {e}") from e
