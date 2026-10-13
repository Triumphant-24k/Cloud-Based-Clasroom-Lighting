import cv2
import os
import time

class CameraSource:
    def __init__(self):
        self.capture, self.image, self.loop = None, None, False
        self.first_frame = None

    def close(self):
        if self.capture is not None:
            self.capture.release()
        self.capture, self.image = None, None
        self.first_frame = None

    def open(self, mode, source, config):
        self.close()
        if mode == 'IMAGE_FILE':
            self.image = cv2.imread(str(source))
            if self.image is None:
                raise ValueError('Cannot decode image')
        else:
            if mode == 'LIVE_CAMERA' and os.name == 'nt':
                # Phone Link supplies frames reliably through DirectShow on this laptop.
                self.capture = cv2.VideoCapture(source, cv2.CAP_DSHOW)
            else:
                self.capture = cv2.VideoCapture(source if mode == 'LIVE_CAMERA' else str(source))
            if not self.capture.isOpened():
                self.close()
                raise ValueError('Cannot open camera/video; use simulation or upload a supported file')
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, config['frame_width'])
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, config['frame_height'])
        if mode == 'LIVE_CAMERA':
            for _ in range(15):
                ok, frame = self.capture.read()
                if ok and frame is not None:
                    self.first_frame = frame
                    break
                time.sleep(.1)
            else:
                self.close()
                raise ValueError('Camera opened but no frames arrived. Enable Phone Link connected camera, allow camera access on your phone, and close other camera apps.')
        self.loop = mode == 'VIDEO_FILE'

    def read(self):
        if self.first_frame is not None:
            frame, self.first_frame = self.first_frame, None
            return frame
        if self.image is not None:
            return self.image.copy()
        if self.capture is None:
            return None
        ok, frame = self.capture.read()
        if not ok and self.loop:
            self.capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = self.capture.read()
        return frame if ok else None
