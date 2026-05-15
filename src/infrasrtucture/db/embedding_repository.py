import logging

import httpx

from src.domain.schemas.items_entities import ItemEmbeddingResult


logger = logging.getLogger(__name__)

class DBEmbeddingRepository:
    def __init__(self, api_path: str) -> None:
        self._api = api_path.rstrip("/")

    async def save(self, result: ItemEmbeddingResult) -> None:
        payload = result.model_dump(mode="json")
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.patch(
                self._api,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
        response.raise_for_status()

        logger.info(f"Saved item embedding: {payload}")
