"""IAM-authenticated AWS Lambda command path; metadata only."""
import asyncio
import json
import os
from urllib.parse import urlparse
import httpx
from .lighting import decide

class CloudService:
    def __init__(self, config, mapping):
        self.config, self.mapping, self.failure = config, mapping, False
        self.status, self.last_error = 'SIMULATED CLOUD', None

    def sign_request(self, url, payload):
        import boto3
        from botocore.auth import SigV4Auth
        from botocore.awsrequest import AWSRequest
        region = os.getenv('AWS_REGION', 'ap-south-1')
        session = boto3.Session(profile_name=os.getenv('AWS_PROFILE') or None, region_name=region)
        credentials = session.get_credentials()
        if credentials is None:
            raise ConnectionError('AWS credentials unavailable')
        request = AWSRequest(method='POST', url=url, data=payload, headers={'Content-Type':'application/json'})
        SigV4Auth(credentials.get_frozen_credentials(), 'lambda', region).add_auth(request)
        return dict(request.headers.items())

    async def decision(self, metadata):
        try:
            if self.failure:
                raise ConnectionError('Simulated outage')
            if self.config['cloud_mode'] == 'CLOUD_CONNECTED':
                url = os.getenv('AWS_LAMBDA_FUNCTION_URL', '')
                parsed = urlparse(url)
                if parsed.scheme != 'https' or not parsed.hostname or not parsed.hostname.endswith('.on.aws'):
                    raise ConnectionError('Configure an HTTPS AWS Lambda Function URL')
                fields = ('classroomId','timestamp','peopleDetected','occupiedZones','ambientLight','systemMode')
                payload = json.dumps({k:metadata[k] for k in fields if k in metadata}, allow_nan=False).encode()
                headers = await asyncio.wait_for(asyncio.to_thread(self.sign_request, url, payload), timeout=4)
                async with httpx.AsyncClient(timeout=3) as client:
                    response = await client.post(url, content=payload, headers=headers)
                    response.raise_for_status()
                    lights = response.json()['lights']
                if set(lights) != set(self.mapping.values()) or any(type(v) not in (int,float) or not 0<=v<=100 for v in lights.values()):
                    raise ValueError('Invalid cloud lighting command')
                if lights != decide(metadata['occupiedZones'],metadata['ambientLight'],self.config,self.mapping):
                    raise ValueError('Cloud/local configuration mismatch')
                self.status, self.last_error = 'CLOUD CONNECTED', None
                return lights
            self.status, self.last_error = 'SIMULATED CLOUD', None
            return decide(metadata['occupiedZones'],metadata['ambientLight'],self.config,self.mapping)
        except Exception as exc:
            self.last_error = type(exc).__name__
            self.status = 'CLOUD OFFLINE · LOCAL FALLBACK ACTIVE'
            return decide(metadata['occupiedZones'],metadata['ambientLight'],self.config,self.mapping)

    async def close(self):
        pass
