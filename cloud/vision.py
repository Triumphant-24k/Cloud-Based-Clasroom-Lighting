"""CPU-only YOLOv8n inference and perspective geometry inside AWS Lambda."""
import base64
import time
from pathlib import Path
import cv2
import numpy as np
from backend.cv.zone_mapper import assign_people, floor_zones

_net = None

def detect(frame, confidence=.35):
    global _net
    if _net is None:
        cv2.setNumThreads(2)
        _net = cv2.dnn.readNetFromONNX(str(Path(__file__).parent/'yolov8n.onnx'))
    h, w = frame.shape[:2]
    scale = min(640/w, 640/h)
    nw, nh = round(w*scale), round(h*scale)
    left, top = (640-nw)//2, (640-nh)//2
    canvas = np.full((640,640,3),114,np.uint8)
    canvas[top:top+nh,left:left+nw] = cv2.resize(frame,(nw,nh))
    _net.setInput(cv2.dnn.blobFromImage(canvas,1/255,(640,640),swapRB=True,crop=False))
    rows = _net.forward()[0].T
    boxes, scores = [], []
    for row in rows:
        if row[4] < confidence or int(np.argmax(row[4:])) != 0:
            continue
        cx,cy,bw,bh = row[:4]
        boxes.append([float((cx-bw/2-left)/scale),float((cy-bh/2-top)/scale),float(bw/scale),float(bh/scale)])
        scores.append(float(row[4]))
    indices = cv2.dnn.NMSBoxes(boxes,scores,confidence,.7)
    result=[]
    for index in np.asarray(indices).reshape(-1):
        x,y,bw,bh = boxes[int(index)]
        result.append([max(0,x),max(0,y),min(w,x+bw),min(h,y+bh)])
    return result

def analyze(payload, default_zones):
    start=time.perf_counter()
    encoded=payload['image']
    if not isinstance(encoded,str) or len(encoded)>2_000_000:
        raise ValueError('Image exceeds analysis limit')
    data=base64.b64decode(encoded,validate=True)
    # Bound decoded dimensions before allocating an image through OpenCV.
    from PIL import Image
    from io import BytesIO
    with Image.open(BytesIO(data)) as image:
        if image.width>1920 or image.height>1080 or image.format not in ('JPEG','PNG'):
            raise ValueError('Unsupported image dimensions or format')
        image.verify()
    frame=cv2.imdecode(np.frombuffer(data,np.uint8),cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError('Cannot decode image')
    corners=payload.get('floorCorners',[])
    zones=floor_zones(corners) if corners else default_zones
    boxes=detect(frame)
    h,w=frame.shape[:2]
    counts=assign_people(boxes,zones,w,h)
    ambient=float(cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY).mean())/255*1000
    return {'boxes':boxes,'zones':zones,'zoneCounts':counts,'peopleDetected':len(boxes),
            'occupiedZones':{z:n>0 for z,n in counts.items()},'ambientLight':ambient,
            'inferenceLatency':(time.perf_counter()-start)*1000,
            'floorMapping':'CALIBRATED' if corners else 'UNCALIBRATED',
            'computeLocation':'AWS_LAMBDA','model':'yolov8n-onnx'}
