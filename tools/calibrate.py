"""Run with python -m tools.calibrate --image classroom.jpg (or --camera 0)."""
import argparse
import json
import cv2
from backend.config import ROOT, ZONES

def main():
    parser=argparse.ArgumentParser(description='Click polygon points; Enter saves zone; Backspace undoes; Esc quits.')
    parser.add_argument('--image');parser.add_argument('--camera',type=int,default=0)
    args=parser.parse_args()
    if args.image: frame=cv2.imread(args.image)
    else:
        cap=cv2.VideoCapture(args.camera);ok,frame=cap.read();cap.release()
        if not ok: frame=None
    if frame is None: raise SystemExit('Cannot load frame. Supply --image with a real classroom image.')
    h,w=frame.shape[:2]; scale=min(1,1200/w,800/h)
    frame=cv2.resize(frame,(int(w*scale),int(h*scale)));h,w=frame.shape[:2]
    points=[]; polygons={};index=0
    def click(event,x,y,flags,param):
        if event==cv2.EVENT_LBUTTONDOWN: points.append([x/w,y/h])
    cv2.namedWindow('Calibration');cv2.setMouseCallback('Calibration',click)
    while index<len(ZONES):
        view=frame.copy()
        for polygon in polygons.values():
            import numpy as np
            cv2.polylines(view,[np.array([[x*w,y*h] for x,y in polygon],dtype=np.int32)],True,(80,190,80),2)
        for x,y in points: cv2.circle(view,(int(x*w),int(y*h)),5,(0,220,255),-1)
        cv2.putText(view,f'{ZONES[index]}: click 3+ points; ENTER next; BACKSPACE undo; ESC cancel',(10,25),0,.5,(0,220,255),1)
        cv2.imshow('Calibration',view);key=cv2.waitKey(30)&255
        if key==27: cv2.destroyAllWindows();return
        if key==8 and points: points.pop()
        if key in (10,13) and len(points)>=3:
            polygons[ZONES[index]]=points.copy();points.clear();index+=1
    (ROOT/'config/classroom_zones.json').write_text(json.dumps(polygons,indent=2))
    cv2.destroyAllWindows();print('Saved all six normalized zone polygons. Restart backend.')

if __name__=='__main__': main()
