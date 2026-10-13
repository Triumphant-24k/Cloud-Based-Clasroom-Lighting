"""IAM-authenticated AWS Lambda command path; metadata only."""
import asyncio
import json
import os
import time
from urllib.parse import urlparse
import httpx
from .lighting import decide

class CloudService:
    def __init__(self, config, mapping):
        self.config, self.mapping, self.failure = config, mapping, False
        self.status, self.last_error = 'SIMULATED CLOUD', None
        self._credit_checked_at = 0
        self._billing = None

    def check_credit_budget(self):
        if self._credit_checked_at and time.monotonic() - self._credit_checked_at < 60:
            return
        import boto3
        from botocore.config import Config
        if self._billing is None:
            session = boto3.Session(profile_name=os.getenv('AWS_PROFILE') or None,
                                    region_name=os.getenv('AWS_REGION', 'ap-southeast-2'))
            self._billing = session.client('freetier', config=Config(
                connect_timeout=2, read_timeout=2, retries={'total_max_attempts':1}))
        plan = self._billing.get_account_plan_state()
        if plan['accountPlanType'] != 'FREE' or plan['accountPlanStatus'] != 'ACTIVE':
            raise ConnectionError('AWS must remain on the active Free plan')
        earned = sum(float(activity.get('reward',{}).get('credit',{}).get('amount',0))
                     for page in self._billing.get_paginator('list_account_activities').paginate()
                     for activity in page['activities'] if activity['status']=='COMPLETED')
        remaining = float(plan['accountPlanRemainingCredits']['amount'])
        spent = max(0, 100 + earned - remaining)
        # Stop below the user budget because AWS billing data can lag.
        ceiling = min(100, self.config.get('aws_credit_budget',100))
        buffer = max(20, self.config.get('aws_credit_buffer',20))
        if remaining <= 0 or spent >= ceiling-buffer:
            raise ConnectionError('AWS credit spending safeguard reached')
        self._credit_checked_at = time.monotonic()

    def sign_request(self, url, payload):
        import boto3
        from botocore.auth import SigV4Auth
        from botocore.awsrequest import AWSRequest
        region = os.getenv('AWS_REGION', 'ap-southeast-2')
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
                await asyncio.wait_for(asyncio.to_thread(self.check_credit_budget), timeout=8)
                url = os.getenv('AWS_LAMBDA_FUNCTION_URL', '')
                parsed = urlparse(url)
                if parsed.scheme != 'https' or not parsed.hostname or not parsed.hostname.endswith('.on.aws'):
                    raise ConnectionError('Configure an HTTPS AWS Lambda Function URL')
                fields = ('classroomId','timestamp','peopleDetected','occupiedZones','ambientLight','systemMode','classTime')
                payload = json.dumps({k:metadata[k] for k in fields if k in metadata}, allow_nan=False).encode()
                headers = await asyncio.wait_for(asyncio.to_thread(self.sign_request, url, payload), timeout=4)
                async with httpx.AsyncClient(timeout=12) as client:
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
