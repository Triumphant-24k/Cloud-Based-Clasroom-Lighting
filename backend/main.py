import asyncio
import time
import uuid
import os
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from collections import deque
import cv2
import numpy as np
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from backend.config import ROOT, ZONES, load_config
from backend.cv.camera import CameraSource
from backend.cv.detector import PersonDetector
from backend.cv.zone_mapper import assign_people
from backend.cv.smoothing import OccupancySmoother
from backend.services.lighting import LightingController
from backend.services.cloud import CloudService
from backend.services.energy import EnergyTracker
from backend.services.telemetry import History

load_dotenv(ROOT/'.env')

class Engine:
    def __init__(self):
        self.config, self.zones, self.mapping = load_config()
        self.source, self.detector = CameraSource(), PersonDetector(self.config)
        self.smoother = OccupancySmoother(ZONES,self.config['zone_on_delay'],self.config['zone_off_delay'])
        self.lighting, self.cloud = LightingController(self.config,self.mapping), CloudService(self.config,self.mapping)
        self.energy, self.history = EnergyTracker(self.config['light_wattage']), History()
        self.lock = asyncio.Lock()
        self.logs = deque(maxlen=100)
        self.mode, self.running, self.ambient = 'SIMULATION', True, 450
        self.class_time = datetime.now(timezone.utc).isoformat()
        self.scenario, self.boxes, self.latency = ['FRONT_LEFT','MIDDLE_RIGHT','BACK_LEFT'], [], 0
        self.frame = np.zeros((540,960,3),np.uint8)
        self.state, self.jpeg, self.counter = {}, b'', 0
        self.last_save, self.last_device, self.last_cloud = 0, '', ''
        self.last_telemetry_log = 0
        self.last_people = -1
        self.log('System ready · anonymous zone occupancy only')

    def log(self, message):
        self.logs.appendleft({'timestamp':datetime.now(timezone.utc).isoformat(),'message':message})

    def simulated_frame(self):
        frame = np.full((540,960,3), (28,32,42),np.uint8)
        cv2.rectangle(frame,(330,10),(630,35),(85,105,115),-1)
        cv2.putText(frame,'BOARD',(425,29),0,.6,(240,240,240),1)
        boxes=[]
        for z in self.scenario:
            p = self.zones[z]
            x,y = np.mean(p,axis=0)*[960,540]
            boxes.append([x-22,y-58,x+22,y+10])
            cv2.circle(frame,(int(x),int(y-45)),12,(150,165,180),-1)
            cv2.rectangle(frame,(int(x-15),int(y-30)),(int(x+15),int(y+8)),(100,120,140),-1)
        return frame, boxes

    async def tick(self):
        start = time.monotonic()
        if self.running:
            if self.mode == 'SIMULATION':
                self.frame,self.boxes = self.simulated_frame()
                self.latency = 0
            else:
                frame = await asyncio.to_thread(self.source.read)
                if frame is None:
                    self.running=False
                    self.log('Source unavailable; detection paused')
                else:
                    self.frame=cv2.resize(frame,(self.config['frame_width'],self.config['frame_height']))
                    # Relative camera brightness estimate; this is not a calibrated lux reading.
                    self.ambient = float(cv2.cvtColor(self.frame, cv2.COLOR_BGR2GRAY).mean()) / 255 * 1000
                    if self.counter % self.config['process_every_n_frames'] == 0:
                        try:
                            self.boxes,self.latency = await asyncio.to_thread(self.detector.detect,self.frame)
                        except Exception as exc:
                            self.running=False
                            self.log(f'YOLO failed: {type(exc).__name__}; check model/dependencies')
                    self.counter+=1
        h,w=self.frame.shape[:2]
        raw=assign_people(self.boxes,self.zones,w,h,self.config['assignment_method'],self.config['overlap_threshold'])
        if len(self.boxes)!=self.last_people:
            self.log(f'Person detection count: {len(self.boxes)}')
            self.last_people=len(self.boxes)
        previous=self.smoother.state.copy()
        occupied=self.smoother.update(raw,start) if self.running else previous
        for z in ZONES:
            if occupied[z]!=previous[z]: self.log(f'{z} '+('occupied' if occupied[z] else 'empty'))
        metadata={'classroomId':self.config['classroom_id'],'timestamp':datetime.now(timezone.utc).isoformat(),'classTime':self.class_time,'peopleDetected':len(self.boxes),'occupiedZones':occupied,'ambientLight':self.ambient,'systemMode':self.lighting.mode}
        if self.config['cloud_mode']=='LOCAL_DEMO' or self.cloud.failure or (self.running and self.mode in ('IMAGE_FILE','LIVE_CAMERA')):
            cloud_lights=await self.cloud.decision(metadata)
        else:
            cloud_lights=self.lighting.calculate(occupied,self.ambient)
        if start-self.last_telemetry_log>=10:
            self.log('Telemetry sent to simulated cloud' if self.cloud.status=='SIMULATED CLOUD' else 'Telemetry sent to cloud' if self.cloud.status=='CLOUD CONNECTED' else 'Local fallback decision received')
            if 'OFFLINE' not in self.cloud.status: self.log('Cloud decision received')
            self.last_telemetry_log=start
        lights=self.lighting.manual.copy() if self.lighting.mode=='MANUAL' else cloud_lights
        if self.last_cloud != self.cloud.status:
            self.log(self.cloud.status)
            self.last_cloud=self.cloud.status
        old=self.state.get('lights',{})
        for l,v in lights.items():
            if old.get(l)!=v: self.log(f'{l} → {v}%')
        device='ESP32 SIMULATED'
        if self.config['esp32_mode']=='ESP32_CONNECTED':
            try:
                async with httpx.AsyncClient(timeout=2) as client:
                    r=await client.post(os.getenv('ESP32_URL','http://192.168.1.100')+'/lights',json={'lights':lights,'occupiedZones':occupied,'ambientLight':self.ambient})
                    r.raise_for_status()
                device='ESP32 CONNECTED'
            except Exception: device='ESP32 OFFLINE · COMMAND NOT DELIVERED'
        if device!=self.last_device:
            self.log(device); self.last_device=device
        elapsed=max(.001,time.monotonic()-start)
        self.state={**metadata,'occupiedZoneCount':sum(occupied.values()),'occupancyPercentage':sum(occupied.values())/6*100,'lights':lights,'energy':self.energy.update(lights,start),'cloudStatus':self.cloud.status,'cloudMode':self.config['cloud_mode'],'esp32Mode':self.config['esp32_mode'],'esp32Status':device,'cameraStatus':('RUNNING' if self.running else 'PAUSED')+' · '+self.mode,'sourceMode':self.mode,'detectionRunning':self.running,'cvFPS':min(1/self.config['tick_seconds'],1/elapsed) if self.running else 0,'inferenceLatency':self.latency,'zones':self.zones,'mapping':self.mapping,'logs':list(self.logs)}
        overlay=self.frame.copy()
        for z,p in self.zones.items():
            poly=np.array([[x*w,y*h] for x,y in p],np.int32)
            color=(110,210,65) if occupied[z] else (115,105,90)
            cv2.polylines(overlay,[poly],True,color,2)
            x,y=np.min(poly,axis=0)+[10,30]
            cv2.putText(overlay,z.replace('_',' '),(int(x),int(y)),0,.48,color,1)
            cv2.putText(overlay,f'{"OCCUPIED" if occupied[z] else "EMPTY"} | LIGHT {lights[self.mapping[z]]}%',(int(x),int(y+22)),0,.42,color,1)
        for x1,y1,x2,y2 in self.boxes:
            cv2.rectangle(overlay,(int(x1),int(y1)),(int(x2),int(y2)),(220,170,75),2)
            cv2.circle(overlay,(int((x1+x2)/2),int(y2)),4,(0,220,255),-1)
        _,encoded=cv2.imencode('.jpg',overlay)
        self.jpeg=encoded.tobytes()
        if start-self.last_save>=1:
            self.history.save({k:v for k,v in self.state.items() if k not in ('logs','zones','mapping')})
            self.last_save=start

engine=None

async def loop():
    while True:
        try:
            async with engine.lock: await engine.tick()
        except Exception as exc: engine.log(f'Processing error: {type(exc).__name__}')
        await asyncio.sleep(engine.config['tick_seconds'])

@asynccontextmanager
async def lifespan(app):
    global engine
    engine=Engine()
    await engine.tick()
    task=asyncio.create_task(loop())
    yield
    task.cancel()
    try: await task
    except asyncio.CancelledError: pass
    engine.source.close()
    await engine.cloud.close()
    engine.history.db.close()

app=FastAPI(title='ZoneLight Classroom API',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:5173','http://127.0.0.1:5173'],allow_methods=['*'],allow_headers=['*'])

class Control(BaseModel):
    action:str
    value:str|float|None=None
    lights:dict[str,int]|None=None

@app.get('/api/state')
def state(): return engine.state

@app.get('/api/history')
def history(limit:int=120): return engine.history.read(max(1,min(limit,1000)))

@app.get('/api/preview')
def preview(): return Response(engine.jpeg,media_type='image/jpeg',headers={'Cache-Control':'no-store'})

@app.get('/api/config')
def config(): return {'settings':engine.config,'zones':engine.zones,'mapping':engine.mapping}

@app.post('/api/control')
async def control(body:Control):
    async with engine.lock:
        a,v=body.action,body.value
        if a=='scenario':
            scenarios={'front':ZONES[:2],'middle':ZONES[2:4],'back':ZONES[4:],'scattered':[ZONES[0],ZONES[3],ZONES[4]],'full':ZONES,'empty':[]}
            if v not in scenarios: raise HTTPException(400,'Unknown scenario')
            engine.source.close(); engine.mode='SIMULATION';engine.scenario=scenarios[v];engine.running=True
        elif a=='ambient':
            if not isinstance(v,(int,float)) or not 0<=v<=2000: raise HTTPException(400,'Ambient level must be 0–2000')
            engine.ambient=v
        elif a=='cloud_failure': engine.cloud.failure=v=='on'
        elif a=='cloud_mode':
            if v not in ('LOCAL_DEMO','CLOUD_CONNECTED'): raise HTTPException(400,'Invalid cloud mode')
            engine.config['cloud_mode']=v
        elif a=='esp32_mode':
            if v not in ('ESP32_CONNECTED','ESP32_SIMULATED'): raise HTTPException(400,'Invalid device mode')
            engine.config['esp32_mode']=v
        elif a=='mode':
            if v not in ('AUTO','MANUAL'): raise HTTPException(400,'Invalid control mode')
            if v=='MANUAL': engine.lighting.manual=engine.state['lights'].copy()
            engine.lighting.mode=v
        elif a=='manual':
            if engine.lighting.mode!='MANUAL': raise HTTPException(409,'Switch to MANUAL first')
            if not body.lights or set(body.lights)!=set(engine.mapping.values()) or any(not 0<=n<=100 for n in body.lights.values()): raise HTTPException(400,'Provide all six brightness values, 0–100')
            engine.lighting.manual=body.lights
        elif a=='start': engine.running=True
        elif a=='pause': engine.running=False
        elif a=='camera':
            try: await asyncio.to_thread(engine.source.open,'LIVE_CAMERA',engine.config['camera_id'],engine.config)
            except ValueError as exc: raise HTTPException(400,str(exc))
            engine.mode='LIVE_CAMERA'; engine.running=True;engine.boxes=[];engine.counter=0
            engine.smoother=OccupancySmoother(ZONES,engine.config['zone_on_delay'],engine.config['zone_off_delay'])
            engine.class_time=datetime.now(timezone.utc).isoformat()
        elif a=='stop_camera':
            engine.source.close();engine.mode='SIMULATION';engine.scenario=[];engine.boxes=[];engine.running=True
        elif a=='reset':
            engine.source.close();engine.mode='SIMULATION';engine.scenario=[];engine.boxes=[];engine.running=True
            engine.smoother=OccupancySmoother(ZONES,engine.config['zone_on_delay'],engine.config['zone_off_delay'])
            engine.lighting.mode='AUTO';engine.cloud.failure=False
        elif a=='sample':
            from tools.sample_video import generate
            path=await asyncio.to_thread(generate)
            engine.source.open('VIDEO_FILE',path,engine.config);engine.mode='VIDEO_FILE';engine.running=True;engine.boxes=[]
        else: raise HTTPException(400,'Unknown action')
        engine.log(f'Control: {a} {v if v is not None else ""}')
        await engine.tick()
        return engine.state

@app.post('/api/upload')
async def upload(file:UploadFile=File(...)):
    suffix=__import__('pathlib').Path(file.filename or '').suffix.lower()
    if suffix not in ('.jpg','.jpeg','.png','.mp4','.avi','.mov','.mkv'): raise HTTPException(400,'Unsupported file type')
    folder=ROOT/'uploads';folder.mkdir(exist_ok=True)
    path=folder/(uuid.uuid4().hex+suffix)
    size=0
    try:
        with path.open('wb') as output:
            while chunk:=await file.read(1024*1024):
                size+=len(chunk)
                if size>engine.config['max_upload_mb']*1024*1024: raise HTTPException(413,'File too large')
                output.write(chunk)
        async with engine.lock:
            mode='IMAGE_FILE' if suffix in ('.jpg','.jpeg','.png') else 'VIDEO_FILE'
            try: engine.source.open(mode,path,engine.config)
            except ValueError as exc: raise HTTPException(400,str(exc))
            engine.mode=mode;engine.running=True;engine.boxes=[];engine.counter=0
            engine.smoother=OccupancySmoother(ZONES,engine.config['zone_on_delay'],engine.config['zone_off_delay'])
            engine.class_time=datetime.now(timezone.utc).isoformat()
            engine.log(f'{mode} loaded locally')
        return {'mode':mode}
    except Exception:
        path.unlink(missing_ok=True)
        raise

@app.websocket('/ws')
async def websocket(ws:WebSocket):
    await ws.accept()
    try:
        while True:
            await ws.send_json(engine.state)
            await asyncio.sleep(.5)
    except (WebSocketDisconnect,RuntimeError): pass
