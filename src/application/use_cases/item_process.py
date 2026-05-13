from src.domain.interfaces.embedding_model import IEmbeddingModel
from src.domain.interfaces.object_storage import IObjectStorage


class ProcessItemUseCase:
    def __init__(
            self,
            object_storage: IObjectStorage,
            embedding_repo: IEmbeddingModel
            session: Infere
    ) -> None: