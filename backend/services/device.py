"""Authenticated local Wi-Fi bridge for six ESP32 PWM outputs."""
import ipaddress
import os
import uuid
import httpx

NETWORKS=tuple(ipaddress.ip_network(n) for n in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16'))

def device_url(address):
    try:
        ip=ipaddress.IPv4Address(address.strip())
    except (ValueError,AttributeError):
        raise ValueError('Enter the ESP32 local IPv4 address shown in Serial Monitor')
    if not any(ip in network for network in NETWORKS):
        raise ValueError('ESP32 must be on your private Wi-Fi network')
    return 'http://'+str(ip)

class DeviceBridge:
    def __init__(self,mapping):
        self.mapping=mapping
        self.url=''
        self.token=os.getenv('ESP32_TOKEN','')
        self.last_reply=None

    def headers(self):
        if len(self.token)<32:
            raise ValueError('Run python -m tools.prepare_esp32 to create the device key')
        return {'X-ZoneLight-Token':self.token}

    async def connect(self,address):
        candidate=device_url(address)
        async with httpx.AsyncClient(timeout=2,trust_env=False,follow_redirects=False) as client:
            response=await client.get(candidate+'/status',headers=self.headers())
            response.raise_for_status()
            status=response.json()
        if status.get('device')!='ZoneLight-ESP32' or status.get('protocol')!=1 or status.get('pwmReady') is not True or set(status.get('lights',{}))!=set(self.mapping.values()):
            raise ValueError('Device is not running the matching six-zone ZoneLight firmware')
        self.url=candidate
        return status

    async def send(self,lights,occupied,ambient,analysis=None):
        if not self.url:
            raise ValueError('Connect the ESP32 using its local IP first')
        command_id=uuid.uuid4().hex
        payload={'commandId':command_id,'lights':lights,'occupiedZones':occupied,'ambientLight':ambient,
                 'cloudRequestId':(analysis or {}).get('requestId','')}
        async with httpx.AsyncClient(timeout=2,trust_env=False,follow_redirects=False) as client:
            response=await client.post(self.url+'/lights',headers=self.headers(),json=payload)
            response.raise_for_status()
            reply=response.json()
        if reply.get('commandId')!=command_id or reply.get('lights')!=lights or reply.get('ok') is not True:
            raise ValueError('ESP32 did not acknowledge all six requested levels')
        self.last_reply={'commandId':command_id,'lights':reply['lights'],'cloudRequestId':payload['cloudRequestId']}
        return self.last_reply

    async def stop(self):
        if self.url:
            try:
                await self.send(dict.fromkeys(self.mapping.values(),0),dict.fromkeys(self.mapping,False),0)
            finally:
                self.url=''
