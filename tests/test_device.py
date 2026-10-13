import asyncio
import json
import httpx
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.config import load_config
from backend.services.device import DeviceBridge, device_url

@pytest.mark.parametrize('address',['127.0.0.1','8.8.8.8','169.254.1.1','http://192.168.1.2','192.168.1.2:80','::1','not-an-ip'])
def test_device_rejects_non_lan_targets(address):
    with pytest.raises(ValueError): device_url(address)

def test_device_private_address():
    assert device_url(' 192.168.1.20 ')=='http://192.168.1.20'

def mock_board(monkeypatch,ack=True):
    import backend.services.device as module
    original=httpx.AsyncClient
    received=[]
    _,_,mapping=load_config()
    monkeypatch.setenv('ESP32_TOKEN','test-device-key-'+'x'*32)
    def handler(request):
        assert request.headers['X-ZoneLight-Token']=='test-device-key-'+'x'*32
        if request.url.path=='/status':
            return httpx.Response(200,json={'device':'ZoneLight-ESP32','protocol':1,'pwmReady':True,'lights':dict.fromkeys(mapping.values(),0)})
        body=json.loads(request.content);received.append(body)
        return httpx.Response(200,json={'ok':True,'commandId':body['commandId'] if ack else 'wrong-id','lights':body['lights']})
    monkeypatch.setattr(module.httpx,'AsyncClient',lambda **kwargs:original(transport=httpx.MockTransport(handler)))
    return mapping,received

def test_device_authenticates_and_checks_acknowledgement(monkeypatch):
    mapping,received=mock_board(monkeypatch)
    bridge=DeviceBridge(mapping)
    asyncio.run(bridge.connect('192.168.1.20'))
    lights={light:i*20 for i,light in enumerate(mapping.values())}
    reply=asyncio.run(bridge.send(lights,dict.fromkeys(mapping,True),450,{'requestId':'aws-result-id'}))
    assert reply['lights']==lights and reply['cloudRequestId']=='aws-result-id'
    assert received[0]['cloudRequestId']=='aws-result-id' and received[0]['commandId']
    asyncio.run(bridge.stop())
    assert not bridge.url and all(v==0 for v in received[-1]['lights'].values())

def test_device_rejects_unacknowledged_commands(monkeypatch):
    mapping,_=mock_board(monkeypatch,False)
    bridge=DeviceBridge(mapping)
    asyncio.run(bridge.connect('192.168.1.20'))
    with pytest.raises(ValueError,match='acknowledge'):
        asyncio.run(bridge.send(dict.fromkeys(mapping.values(),100),dict.fromkeys(mapping,True),0))
    assert bridge.last_reply is None

def test_connection_panel_routes_and_led_shutdown(monkeypatch):
    _,received=mock_board(monkeypatch)
    with TestClient(app) as client:
        response=client.post('/api/device/connect',json={'address':'192.168.1.20'})
        state=response.json()
        assert response.status_code==200 and state['esp32Mode']=='ESP32_CONNECTED'
        assert state['esp32Address']=='192.168.1.20' and 'ACKNOWLEDGED' in state['esp32Status']
        assert state['esp32Delivery']['lights']==state['lights']
        assert client.post('/api/device/connect',json={'address':'8.8.8.8'}).status_code==400
        response=client.post('/api/device/disconnect')
        assert response.json()['esp32Mode']=='ESP32_SIMULATED'
        assert all(v==0 for v in received[-1]['lights'].values())

def test_failed_cloud_vision_switches_off_real_outputs(monkeypatch):
    import backend.main as main
    _,received=mock_board(monkeypatch)
    with TestClient(app) as client:
        client.post('/api/device/connect',json={'address':'192.168.1.20'})
        main.engine.mode='IMAGE_FILE'
        main.engine.running=False
        main.engine.vision_location='CLOUD_UNAVAILABLE'
        main.engine.lighting.mode='AUTO'
        asyncio.run(main.engine.tick())
        assert all(v==0 for v in received[-1]['lights'].values())
        assert main.engine.state['lights']==received[-1]['lights']
