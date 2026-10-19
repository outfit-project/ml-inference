from uuid import UUID

import httpx

from src.domain.errors import PermanentError, TransientError
from src.domain.schemas.items_entities import ItemEmbeddingResult


class DBEmbeddingRepository:
    def __init__(self, api_path: str, service_token: str):
        if not service_token:
            raise ValueError('ML_SERVICE_TOKEN must be configured')
        self._api = api_path.rstrip('/')
        self._token = service_token

    async def _update(self, payload: dict) -> None:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.patch(
                self._api, json=payload, headers={'X-Service-Token': self._token},
            )
        if response.status_code != 404:
            response.raise_for_status()

    async def save(self, result: ItemEmbeddingResult) -> None:
        try:
            await self._update(result.model_dump(mode='json'))
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code >= 500:
                raise TransientError(f'Wardrobe API error: {exc}') from exc
            raise PermanentError('Processing result could not be saved. Please retry.') from exc
        except httpx.HTTPError as exc:
            raise TransientError(f'Wardrobe API error: {exc}') from exc

    async def set_status(self, item_id: UUID, status: str, error: str | None = None) -> None:
        try:
            await self._update({
                'item_id': str(item_id), 'processing_status': status, 'processing_error': error,
            })
        except httpx.HTTPError as exc:
            raise TransientError('Wardrobe callback unavailable') from exc
