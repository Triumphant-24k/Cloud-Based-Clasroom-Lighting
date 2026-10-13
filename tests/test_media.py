import cv2
import numpy as np
from fastapi.testclient import TestClient
from backend.main import app
from backend.cv.camera import CameraSource
from backend.config import load_config
from tools.sample_video import generate

def test_image_decode(tmp_path):
 path=tmp_path/'frame.png';cv2.imwrite(str(path),np.zeros((120,200,3),np.uint8))
 source=CameraSource();source.open('IMAGE_FILE',path,load_config()[0]);assert source.read().shape==(120,200,3);source.close()

def test_video_decode_and_loop():
 source=CameraSource();source.open('VIDEO_FILE',generate(),load_config()[0])
 for _ in range(102): assert source.read() is not None
 source.close()

def test_upload_image_with_mocked_detector(monkeypatch):
 # Test media pipeline without network/model weight dependency.
 from backend.cv.detector import PersonDetector
 monkeypatch.setattr(PersonDetector,'detect',lambda self,frame:([[20,20,100,100]],5))
 _,png=cv2.imencode('.png',np.zeros((540,960,3),np.uint8))
 with TestClient(app) as client:
  response=client.post('/api/upload',files={'file':('test.png',png.tobytes(),'image/png')})
  assert response.json()['mode']=='IMAGE_FILE'
  state=client.post('/api/control',json={'action':'start'}).json()
  assert state['peopleDetected']==1 and state['sourceMode']=='IMAGE_FILE'
  assert state['ambientLight']==0 and state['classTime']
  assert len(state['lights'])==6


def test_uploaded_image_is_analyzed_once_and_uses_auto(monkeypatch):
 import backend.main as main
 from backend.cv.detector import PersonDetector
 from backend.services.cloud import CloudService
 from cloud.decision import decide
 calls=[]
 monkeypatch.setattr(PersonDetector,'detect',lambda self,frame:([[20,20,100,100]],5))
 async def cloud(self,metadata):
  calls.append(metadata)
  return decide(metadata['occupiedZones'],metadata['ambientLight'],self.config,self.mapping)
 monkeypatch.setattr(CloudService,'decision',cloud)
 _,png=cv2.imencode('.png',np.zeros((540,960,3),np.uint8))
 with TestClient(app) as client:
  calls.clear();main.engine.lighting.mode='MANUAL'
  response=client.post('/api/upload',files={'file':('classroom.png',png.tobytes(),'image/png')})
  state=response.json()['state']
  assert response.status_code==200 and state['systemMode']=='AUTO'
  assert state['peopleDetected']==1 and state['occupiedZoneCount']==1
  assert state['lights']['LIGHT_1']==100 and not state['detectionRunning']
  assert len(calls)==1
  import asyncio
  asyncio.run(main.engine.tick())
  assert len(calls)==1
