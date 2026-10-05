import cv2

class CameraSource:
    def __init__(self):
        self.capture, self.image, self.loop = None, None, False

    def close(self):
        if self.capture is not None:
            self.capture.release()
        self.capture, self.image = None, None

    def open(self, mode, source, config):
        self.close()
        if mode == 'IMAGE_FILE':
            self.image = cv2.imread(str(source))
            if self.image is None:
                raise ValueError('Cannot decode image')
        else:
            self.capture = cv2.VideoCapture(source if mode == 'LIVE_CAMERA' else str(source))
            if not self.capture.isOpened():
                self.close()
                raise ValueError('Cannot open camera/video; use simulation or upload a supported file')
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, config['frame_width'])
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, config['frame_height'])
        self.loop = mode == 'VIDEO_FILE'

    def read(self):
        if self.image is not None:
            return self.image.copy()
        if self.capture is None:
            return None
        ok, frame = self.capture.read()
        if not ok and self.loop:
            self.capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = self.capture.read()
        return frame if ok else None
