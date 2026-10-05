"""Generate a synthetic classroom clip; this tests video input, not YOLO accuracy."""
import cv2
import numpy as np
from backend.config import ROOT

def generate():
    folder=ROOT/'data';folder.mkdir(exist_ok=True)
    path=folder/'sample_classroom.avi'
    writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*'MJPG'),10,(960,540))
    if not writer.isOpened(): raise RuntimeError('Video encoder unavailable')
    for i in range(100):
        frame=np.full((540,960,3),40,np.uint8)
        cv2.putText(frame,'SYNTHETIC CLASSROOM - use scenarios for occupancy demo',(30,40),0,.65,(220,220,220),1)
        for row in range(3):
            for col in range(2):
                x,y=col*480+240,row*170+120
                cv2.rectangle(frame,(x-70,y-25),(x+70,y+25),(70,95,110),-1)
        writer.write(frame)
    writer.release()
    return path

if __name__=='__main__': print(generate())
