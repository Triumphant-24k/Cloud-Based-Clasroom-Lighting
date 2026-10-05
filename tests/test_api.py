from fastapi.testclient import TestClient
from backend.main import app

def test_api_controls_history_preview_and_validation():
 with TestClient(app) as c:
  assert c.get('/api/state').status_code==200
  assert c.get('/api/preview').headers['content-type']=='image/jpeg'
  assert c.get('/api/history').json()
  assert c.post('/api/control',json={'action':'scenario','value':'bad'}).status_code==400
  assert c.post('/api/control',json={'action':'manual','lights':{'LIGHT_1':50}}).status_code==409
  c.post('/api/control',json={'action':'mode','value':'MANUAL'})
  lights={f'LIGHT_{i}':i*10 for i in range(1,7)}
  assert c.post('/api/control',json={'action':'manual','lights':lights}).json()['lights']==lights
  assert c.post('/api/control',json={'action':'mode','value':'AUTO'}).json()['systemMode']=='AUTO'
  assert 'FALLBACK' in c.post('/api/control',json={'action':'cloud_failure','value':'on'}).json()['cloudStatus']
  assert c.post('/api/control',json={'action':'reset'}).json()['occupiedZoneCount']==0
  assert c.post('/api/upload',files={'file':('bad.txt',b'bad')}).status_code==400
  with c.websocket_connect('/ws') as ws: assert 'occupiedZones' in ws.receive_json()
