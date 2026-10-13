import asyncio
import pytest
from backend.config import load_config,ZONES
from backend.cv.zone_mapper import point_in_polygon,assign_people
from backend.cv.smoothing import OccupancySmoother
from backend.services.lighting import decide,LightingController
from backend.services.cloud import CloudService
from backend.services.energy import EnergyTracker

def test_configuration():
 c,z,m=load_config();assert len(z)==len(m)==6;assert c['process_every_n_frames']>=1

@pytest.mark.parametrize('point,inside',[((.2,.2),True),((0,0),True),((2,2),False)])
def test_polygon(point,inside): assert point_in_polygon(point,[[0,0],[1,0],[1,1],[0,1]])==inside

def test_assignment():
 c,z,m=load_config();counts=assign_people([[10,5,40,20],[70,60,90,90]],z,100,100)
 assert counts['FRONT_LEFT']==1 and counts['BACK_RIGHT']==1 and sum(counts.values())==2

def test_overlap():
 c,z,m=load_config();counts=assign_people([[10,5,40,20]],z,100,100,'overlap');assert counts['FRONT_LEFT']==1

def test_smoothing_on_off_and_miss():
 s=OccupancySmoother(['A'],1,5)
 assert not s.update({'A':True},0)['A']
 assert not s.update({'A':True},.99)['A']
 assert s.update({'A':True},1)['A']
 assert s.update({'A':False},2)['A']
 assert s.update({'A':True},3)['A']
 assert s.update({'A':False},4)['A']
 assert s.update({'A':False},8.9)['A']
 assert not s.update({'A':False},9)['A']

@pytest.mark.parametrize('ambient,expected',[(850,30),(450,60),(80,100)])
def test_adaptive_and_empty(ambient,expected):
 c,z,m=load_config();out=decide({'FRONT_LEFT':True},ambient,c,m)
 assert out['LIGHT_1']==expected;assert all(v==0 for k,v in out.items() if k!='LIGHT_1')

def test_manual_auto_recovery():
 c,z,m=load_config();l=LightingController(c,m);l.mode='MANUAL';l.manual['LIGHT_2']=77
 assert l.calculate({},80)['LIGHT_2']==77
 l.mode='AUTO';assert l.calculate({'FRONT_LEFT':True},80)['LIGHT_1']==100;assert l.calculate({},80)['LIGHT_2']==0

def test_cloud_failure_and_recovery():
 c,z,m=load_config();c['cloud_mode']='LOCAL_DEMO';cloud=CloudService(c,m);cloud.failure=True
 metadata={'occupiedZones':{'BACK_RIGHT':True},'ambientLight':80}
 assert asyncio.run(cloud.decision(metadata))['LIGHT_6']==100;assert 'FALLBACK' in cloud.status
 cloud.failure=False;assert asyncio.run(cloud.decision(metadata))['LIGHT_6']==100;assert cloud.status=='SIMULATED CLOUD'

def test_unconfigured_aws_falls_back(monkeypatch):
 monkeypatch.delenv('AWS_LAMBDA_FUNCTION_URL',raising=False)
 c,z,m=load_config();c['cloud_mode']='CLOUD_CONNECTED';cloud=CloudService(c,m)
 assert asyncio.run(cloud.decision({'occupiedZones':{},'ambientLight':80}))==dict.fromkeys(m.values(),0)
 assert 'OFFLINE' in cloud.status

def test_energy():
 e=EnergyTracker(40);out=e.update({'LIGHT_1':50},0)
 assert out['baselinePower']==240;assert out['smartPower']==20;assert out['powerSaved']==220
 assert e.update({},3600)['cumulativeEnergySavedWh']==220

def test_cloud_validates_command(monkeypatch):
 import httpx
 import backend.services.cloud as cloud_module
 monkeypatch.setenv('AWS_LAMBDA_FUNCTION_URL','https://test.lambda-url.ap-south-1.on.aws/')
 monkeypatch.setattr(CloudService,'sign_request',lambda self,url,payload: {'Content-Type':'application/json'})
 original=httpx.AsyncClient
 async def handler(request):
  return httpx.Response(200,json={'lights':{'LIGHT_1':999}})
 monkeypatch.setattr(cloud_module.httpx,'AsyncClient',lambda **kwargs:original(transport=httpx.MockTransport(handler)))
 c,z,m=load_config();c['cloud_mode']='CLOUD_CONNECTED';cloud=CloudService(c,m)
 result=asyncio.run(cloud.decision({'occupiedZones':{'FRONT_LEFT':True},'ambientLight':450}))
 assert result['LIGHT_1']==60 and 'FALLBACK' in cloud.status

def test_cloud_connected_metadata_only(monkeypatch):
 import httpx
 import backend.services.cloud as cloud_module
 monkeypatch.setenv('AWS_LAMBDA_FUNCTION_URL','https://test.lambda-url.ap-south-1.on.aws/')
 monkeypatch.setattr(CloudService,'sign_request',lambda self,url,payload: {'Content-Type':'application/json'})
 original=httpx.AsyncClient
 c,z,m=load_config();c['cloud_mode']='CLOUD_CONNECTED'
 async def handler(request):
  import json
  payload=json.loads(request.content)
  assert 'frame' not in payload and 'occupiedZones' in payload
  return httpx.Response(200,json={'lights':dict.fromkeys(m.values(),30)})
 monkeypatch.setattr(cloud_module.httpx,'AsyncClient',lambda **kwargs:original(transport=httpx.MockTransport(handler)))
 cloud=CloudService(c,m)
 assert asyncio.run(cloud.decision({'classroomId':c['classroom_id'],'timestamp':'2026-10-13T00:00:00+00:00','peopleDetected':6,'systemMode':'AUTO','occupiedZones':dict.fromkeys(ZONES,True),'ambientLight':850}))['LIGHT_6']==30
 assert cloud.status=='CLOUD CONNECTED'
