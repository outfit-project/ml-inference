import httpx

from src.domain.schemas.items_entities import ItemEmbeddingResult


class EmbeddingRepository:
    def __init__(self, api_path: str) -> None:
        self._api = api_path

    async def save(self, result: ItemEmbeddingResult) -> None:
        payload = result.model_dump(mode='json')

        with httpx.AsyncClient() as client:
            response = await client.post(self._api, json=payload)

            response.raise_for_status()

