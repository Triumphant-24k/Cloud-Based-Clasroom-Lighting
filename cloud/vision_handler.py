import base64
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from .lambda_handler import handler as legacy_handler, publish_and_store, CONFIG
from .decision import decide
from .vision import analyze

DEFAULT_ZONES=json.loads((Path(__file__).parent/'classroom_zones.json').read_text())

def handler(event, context):
    def response(code, body):
        return {'statusCode':code,'headers':{'Content-Type':'application/json'},'body':json.dumps(body)}
    try:
        body=event.get('body','')
        if event.get('isBase64Encoded'):
            body=base64.b64decode(body,validate=True).decode()
        payload=json.loads(body)
        if not isinstance(payload,dict):
            raise ValueError()
        if 'image' not in payload:
            return legacy_handler(event,context)
        if event.get('requestContext',{}).get('http',{}).get('method')!='POST':
            return response(405,{'error':'POST required'})
        required={'image','classroomId','timestamp','classTime','systemMode','floorCorners'}
        if set(payload)!=required or payload['classroomId']!=CONFIG['classroom_id']:
            raise ValueError()
        if payload['systemMode'] not in ('AUTO','MANUAL'):
            raise ValueError()
        for key in ('timestamp','classTime'):
            if not isinstance(payload[key],str) or len(payload[key])>64 or datetime.fromisoformat(payload[key].replace('Z','+00:00')).tzinfo is None:
                raise ValueError()
        result=analyze(payload,DEFAULT_ZONES)
        metadata={key:payload[key] for key in ('classroomId','timestamp','classTime','systemMode')}
        metadata.update({key:result[key] for key in ('peopleDetected','occupiedZones','ambientLight','computeLocation','model','floorMapping','zoneCounts')})
        lights=decide(result['occupiedZones'],result['ambientLight'],CONFIG['settings'],CONFIG['mapping'])
    except (ValueError,TypeError,KeyError,UnicodeError):
        return response(400,{'error':'Invalid classroom image or floor calibration'})
    try:
        record=publish_and_store(metadata,lights)
    except Exception as exc:
        logging.getLogger(__name__).warning('AWS telemetry/history failed: %s',type(exc).__name__)
        return response(503,{'error':'Cloud history unavailable'})
    result.update(lights=lights,timestamp=payload['timestamp'],classroomId=payload['classroomId'],
                  requestId=context.aws_request_id,recordId=record['recordId'])
    print(json.dumps({'event':'cloud_vision_complete','requestId':context.aws_request_id,
                     'recordId':record['recordId'],'peopleDetected':result['peopleDetected'],
                     'computeLocation':'AWS_LAMBDA','model':result['model'],'floorMapping':result['floorMapping']}))
    return response(200,result)
