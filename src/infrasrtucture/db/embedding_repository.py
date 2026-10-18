import httpx


class DBEmbeddingRepository:
    def __init__(self,api_path: str,service_token: str):
        if not service_token: raise ValueError('ML_SERVICE_TOKEN must be configured')
        self._api=api_path.rstrip('/')
        self._token=service_token

    async def update(self,payload):
        async with httpx.AsyncClient(timeout=30.0) as client:
            response=await client.patch(self._api,json=payload,headers={'X-Service-Token':self._token})
        if response.status_code != 404:
            response.raise_for_status()

    async def save(self,result):
        await self.update(result.model_dump(mode='json'))

    async def set_status(self,item_id,status,error=None):
        await self.update({'item_id':str(item_id),'processing_status':status,'processing_error':error})
