import asyncio
import base64
import copy
import json
from types import SimpleNamespace

import pytest
from backend.config import load_config
from backend.services.cloud import CloudService
from cloud import lambda_handler as handler
from cloud.decision import decide


def metadata():
    c,z,m=load_config()
    return {'classroomId':c['classroom_id'],'timestamp':'2026-10-13T10:00:00Z','peopleDetected':1,
            'occupiedZones':{name:name=='FRONT_LEFT' for name in z},'ambientLight':450,'systemMode':'AUTO'}


def event(payload):
    return {'requestContext':{'http':{'method':'POST'}},'body':json.dumps(payload)}


@pytest.mark.parametrize('ambient,brightness',[(80,100),(450,60),(850,30)])
def test_lambda_matches_local(monkeypatch,ambient,brightness):
    calls=[]
    monkeypatch.setattr(handler,'publish_and_store',lambda m,l:calls.append((m,l)))
    m=metadata();m['ambientLight']=ambient
    response=handler.handler(event(m),None)
    assert response['statusCode']==200
    lights=json.loads(response['body'])['lights']
    assert lights['LIGHT_1']==brightness and sum(lights.values())==brightness
    c,z,mapping=load_config()
    assert lights==decide(m['occupiedZones'],ambient,c,mapping)
    assert calls[0][0]==m


@pytest.mark.parametrize('field,value',[('frame','private pixels'),('classroomId','OTHER'),('peopleDetected',True),('ambientLight',float('nan')),('occupiedZones',{'FRONT_LEFT':True}),('systemMode','BAD')])
def test_invalid_metadata_never_published(monkeypatch,field,value):
    monkeypatch.setattr(handler,'publish_and_store',lambda *args:pytest.fail('Invalid telemetry published'))
    m=metadata();m[field]=value
    assert handler.handler(event(m),None)['statusCode']==400


def test_lambda_base64_and_method(monkeypatch):
    monkeypatch.setattr(handler,'publish_and_store',lambda *args:None)
    e=event(metadata());e['body']=base64.b64encode(e['body'].encode()).decode();e['isBase64Encoded']=True
    assert handler.handler(e,None)['statusCode']==200
    e['requestContext']['http']['method']='GET'
    assert handler.handler(e,None)['statusCode']==405


def test_lambda_aws_failure(monkeypatch):
    def fail(*args): raise ConnectionError()
    monkeypatch.setattr(handler,'publish_and_store',fail)
    assert handler.handler(event(metadata()),None)['statusCode']==503


def test_sigv4_signs_payload_and_temporary_token(monkeypatch):
    import boto3
    from botocore.credentials import Credentials
    credentials=Credentials('test-access','test-secret','test-token')
    monkeypatch.setattr(boto3,'Session',lambda **kwargs:SimpleNamespace(get_credentials=lambda:credentials))
    monkeypatch.setenv('AWS_REGION','ap-south-1')
    c,z,m=load_config();service=CloudService(c,m)
    signed=service.sign_request('https://test.lambda-url.ap-south-1.on.aws/',b'{}')
    assert signed['Authorization'].startswith('AWS4-HMAC-SHA256 ')
    assert '/ap-south-1/lambda/aws4_request' in signed['Authorization']
    assert signed['X-Amz-Security-Token']=='test-token'


def test_no_aws_credentials_falls_back(monkeypatch):
    import boto3
    monkeypatch.setattr(boto3,'Session',lambda **kwargs:SimpleNamespace(get_credentials=lambda:None))
    monkeypatch.setenv('AWS_LAMBDA_FUNCTION_URL','https://test.lambda-url.ap-south-1.on.aws/')
    c,z,m=load_config();c['cloud_mode']='CLOUD_CONNECTED';service=CloudService(c,m)
    assert asyncio.run(service.decision(metadata()))['LIGHT_1']==60
    assert 'FALLBACK' in service.status


def test_iot_topics_dynamodb_and_manual_suppression(monkeypatch):
    import boto3
    publications=[];records=[]
    iot=SimpleNamespace(publish=lambda **kwargs:publications.append(kwargs))
    discovery=SimpleNamespace(describe_endpoint=lambda **kwargs:{'endpointAddress':'example.iot.ap-south-1.amazonaws.com'})
    monkeypatch.setattr(boto3,'client',lambda name,**kwargs:discovery if name=='iot' else iot)
    monkeypatch.setattr(boto3,'resource',lambda *args,**kwargs:SimpleNamespace(Table=lambda name:SimpleNamespace(put_item=lambda **kw:records.append(kw['Item']))))
    monkeypatch.setenv('HISTORY_TABLE','test-table')
    monkeypatch.setattr(handler,'_iot',None)
    m=metadata();lights={'LIGHT_1':60}
    handler.publish_and_store(m,lights)
    assert [p['topic'] for p in publications]==['zonelight/CLASSROOM-01/telemetry','zonelight/CLASSROOM-01/commands']
    assert publications[1]['retain'] is False
    assert records[0]['classroomId']==m['classroomId'] and records[0]['expiresAt']>0
    publications.clear();m['systemMode']='MANUAL'
    handler.publish_and_store(m,lights)
    assert len(publications)==1 and publications[0]['topic'].endswith('/telemetry')


def test_lambda_deployment_configuration_matches_local():
    c,z,m=load_config()
    assert handler.CONFIG['mapping']==m
    assert handler.CONFIG['classroom_id']==c['classroom_id']
    assert all(c[k]==v for k,v in handler.CONFIG['settings'].items())


def test_class_time_is_validated_and_preserved(monkeypatch):
    calls=[]
    monkeypatch.setattr(handler,'publish_and_store',lambda m,l:calls.append(m))
    m=metadata(); m['classTime']='2026-10-13T09:00:00+00:00'
    assert handler.handler(event(m),None)['statusCode']==200
    assert calls[0]['classTime']==m['classTime']
    m['classTime']='not-a-date'
    assert handler.handler(event(m),None)['statusCode']==400
    m['classTime']='2026-10-13T09:00:00'
    assert handler.handler(event(m),None)['statusCode']==400
