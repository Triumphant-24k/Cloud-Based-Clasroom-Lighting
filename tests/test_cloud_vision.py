import base64
import json
from types import SimpleNamespace
import cv2
import numpy as np
from fastapi.testclient import TestClient
from backend.main import app
from backend.config import load_config
from cloud.decision import decide

def test_cloud_handler_detects_maps_and_stores_no_image(monkeypatch):
    import cloud.vision as vision
    import cloud.vision_handler as handler
    saved=[]
    monkeypatch.setattr(vision,'detect',lambda f:[[20,20,100,100]])
    def store(metadata,lights):
        saved.append(metadata)
        return {'recordId':'test-record'}
    monkeypatch.setattr(handler,'publish_and_store',store)
    _,encoded=cv2.imencode('.jpg',np.zeros((540,960,3),np.uint8))
    payload={'image':base64.b64encode(encoded).decode(),'classroomId':'CLASSROOM-01',
             'timestamp':'2026-10-13T00:00:00+00:00','classTime':'2026-10-13T00:00:00+00:00',
             'systemMode':'AUTO','floorCorners':[[0,0],[1,0],[1,1],[0,1]]}
    event={'requestContext':{'http':{'method':'POST'}},'body':json.dumps(payload)}
    response=handler.handler(event,SimpleNamespace(aws_request_id='test-request'))
    body=json.loads(response['body'])
    assert response['statusCode']==200
    assert body['computeLocation']=='AWS_LAMBDA' and body['peopleDetected']==1
    assert body['floorMapping']=='CALIBRATED' and len(body['zones'])==6
    assert body['requestId']=='test-request' and body['recordId']=='test-record'
    assert 'image' not in saved[0] and saved[0]['zoneCounts']['FRONT_LEFT']==1
    payload['floorCorners']=[[0,0]]*4
    event['body']=json.dumps(payload)
    assert handler.handler(event,SimpleNamespace(aws_request_id='test-request'))['statusCode']==400

def test_cloud_upload_never_invokes_local_detector(monkeypatch):
    import backend.main as main
    from backend.cv.detector import PersonDetector
    from backend.services.cloud import CloudService
    def local(*args): raise AssertionError('Local detector must not run in AWS mode')
    monkeypatch.setattr(PersonDetector,'detect',local)
    async def analyze(self,frame,corners,class_time,mode):
        _,zones,mapping=load_config()
        occupied={z:z=='FRONT_LEFT' for z in zones}
        return {'boxes':[[20,20,100,100]],'zones':zones,'zoneCounts':{z:int(v) for z,v in occupied.items()},
                'occupiedZones':occupied,'ambientLight':0,'inferenceLatency':100,
                'lights':decide(occupied,0,self.config,mapping),'timestamp':'2026-10-13T00:00:00+00:00'}
    monkeypatch.setattr(CloudService,'analyze',analyze)
    _,encoded=cv2.imencode('.png',np.zeros((540,960,3),np.uint8))
    with TestClient(app) as client:
        main.engine.config['cloud_mode']='CLOUD_CONNECTED'
        response=client.post('/api/upload',files={'file':('room.png',encoded.tobytes(),'image/png')})
        state=response.json()['state']
        assert state['visionCompute']=='AWS_LAMBDA' and state['peopleDetected']==1
        assert not state['detectionRunning'] and state['lights']['LIGHT_1']==100
