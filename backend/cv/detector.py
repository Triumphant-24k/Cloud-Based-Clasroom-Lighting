import time

class PersonDetector:
    def __init__(self, config):
        self.config, self.model = config, None

    def detect(self, frame):
        if self.model is None:
            from ultralytics import YOLO
            self.model = YOLO(self.config['yolo_model'])
        start = time.perf_counter()
        result = self.model.predict(frame, classes=[0], conf=self.config['confidence_threshold'], verbose=False)[0]
        return result.boxes.xyxy.cpu().tolist(), (time.perf_counter()-start)*1000
