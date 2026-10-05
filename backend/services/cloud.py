import os
import json
import asyncio
import httpx
from .lighting import decide

class CloudService:
    def __init__(self, config, mapping):
        self.config, self.mapping, self.failure, self.client = config, mapping, False, None
        self.status = 'SIMULATED CLOUD'

    async def decision(self, metadata):
        try:
            if self.failure:
                raise ConnectionError('Simulated outage')
            if self.config['cloud_mode'] == 'CLOUD_CONNECTED':
                url = os.getenv('AZURE_FUNCTION_URL')
                if not url:
                    raise ConnectionError('Azure Function URL not configured')
                connection = os.getenv('AZURE_IOT_DEVICE_CONNECTION_STRING')
                if connection:
                    from azure.iot.device.aio import IoTHubDeviceClient
                    if self.client is None:
                        self.client = IoTHubDeviceClient.create_from_connection_string(connection)
                        await asyncio.wait_for(self.client.connect(), timeout=3)
                    await asyncio.wait_for(self.client.send_message(json.dumps(metadata)), timeout=3)
                async with httpx.AsyncClient(timeout=3) as client:
                    response = await client.post(url, json=metadata, headers={'x-functions-key':os.getenv('AZURE_FUNCTION_KEY','')})
                    response.raise_for_status()
                    lights = response.json()['lights']
                if set(lights) != set(self.mapping.values()) or any(type(v) not in (int,float) or not 0<=v<=100 for v in lights.values()):
                    raise ValueError('Invalid cloud lighting command')
                self.status = 'CLOUD CONNECTED'
                return lights
            self.status = 'SIMULATED CLOUD'
            return decide(metadata['occupiedZones'],metadata['ambientLight'],self.config,self.mapping)
        except Exception:
            self.status = 'CLOUD OFFLINE · LOCAL FALLBACK ACTIVE'
            return decide(metadata['occupiedZones'],metadata['ambientLight'],self.config,self.mapping)

    async def close(self):
        if self.client:
            await self.client.shutdown()
