import base64
import json
import math
import logging
import os
import time
import uuid
from pathlib import Path
from decimal import Decimal
try:
    from .decision import decide
except ImportError:
    from decision import decide

CONFIG=json.loads((Path(__file__).parent/'decision_config.json').read_text())
_iot=None

def publish_and_store(metadata,lights):
    import boto3
    from botocore.config import Config
    global _iot
    if _iot is None:
        timeout=Config(connect_timeout=1,read_timeout=1,retries={'max_attempts':0})
        endpoint=boto3.client('iot',config=timeout).describe_endpoint(endpointType='iot:Data-ATS')['endpointAddress']
        _iot=boto3.client('iot-data',endpoint_url='https://'+endpoint,config=timeout)
    prefix='zonelight/'+metadata['classroomId']
    _iot.publish(topic=prefix+'/telemetry',qos=1,payload=json.dumps(metadata).encode())
    if metadata['systemMode']=='AUTO':
        _iot.publish(topic=prefix+'/commands',qos=1,retain=False,payload=json.dumps({'timestamp':metadata['timestamp'],'lights':lights}).encode())
    record={**metadata,'lights':lights,'recordId':metadata['timestamp']+'#'+uuid.uuid4().hex,'expiresAt':int(time.time())+7*86400}
    boto3.resource('dynamodb',config=Config(connect_timeout=1,read_timeout=1,retries={'max_attempts':0})).Table(os.environ['HISTORY_TABLE']).put_item(Item=json.loads(json.dumps(record),parse_float=Decimal))

def handler(event,context):
    def response(code,body):
        return {'statusCode':code,'headers':{'Content-Type':'application/json'},'body':json.dumps(body)}
    try:
        if event.get('requestContext',{}).get('http',{}).get('method')!='POST':
            return response(405,{'error':'POST required'})
        body=event.get('body','')
        if event.get('isBase64Encoded'): body=base64.b64decode(body,validate=True).decode()
        metadata=json.loads(body)
        fields={'classroomId','timestamp','peopleDetected','occupiedZones','ambientLight','systemMode'}
        if not isinstance(metadata,dict) or set(metadata)!=fields: raise ValueError()
        if metadata['classroomId']!=os.getenv('CLASSROOM_ID',CONFIG['classroom_id']) or metadata['classroomId']!=CONFIG['classroom_id']: raise ValueError()
        if not isinstance(metadata['timestamp'],str) or not 1<=len(metadata['timestamp'])<=64: raise ValueError()
        if type(metadata['peopleDetected']) is not int or not 0<=metadata['peopleDetected']<=10000: raise ValueError()
        if metadata['systemMode'] not in ('AUTO','MANUAL'): raise ValueError()
        zones=metadata['occupiedZones']
        if not isinstance(zones,dict) or set(zones)!=set(CONFIG['mapping']) or any(type(v) is not bool for v in zones.values()): raise ValueError()
        ambient=metadata['ambientLight']
        if type(ambient) not in (int,float) or not math.isfinite(ambient) or not 0<=ambient<=2000: raise ValueError()
        lights=decide(zones,ambient,CONFIG['settings'],CONFIG['mapping'])
    except (ValueError,TypeError,KeyError,UnicodeError):
        return response(400,{'error':'Invalid occupancy metadata'})
    try:
        publish_and_store(metadata,lights)
    except Exception as exc:
        logging.getLogger(__name__).warning('AWS telemetry/history failed: %s',type(exc).__name__)
        return response(503,{'error':'AWS telemetry/history unavailable; use local fallback'})
    return response(200,{'lights':lights})
