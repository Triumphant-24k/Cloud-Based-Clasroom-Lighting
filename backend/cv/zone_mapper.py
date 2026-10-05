import cv2
import numpy as np

def point_in_polygon(point, polygon):
    return cv2.pointPolygonTest(np.array(polygon, dtype=np.float32), tuple(map(float, point)), False) >= 0

def assign_people(boxes, zones, width, height, method='foot_point', threshold=0.15):
    counts = dict.fromkeys(zones, 0)
    for x1, y1, x2, y2 in boxes:
        if method == 'foot_point':
            matches = [z for z, p in zones.items() if point_in_polygon(((x1+x2)/2/width, y2/height), p)]
            if matches:
                counts[matches[0]] += 1
        else:
            mask = np.zeros((height, width), np.uint8)
            cv2.rectangle(mask, (max(0,int(x1)),max(0,int(y1))), (min(width-1,int(x2)),min(height-1,int(y2))), 1, -1)
            area = max(1, int(mask.sum()))
            scores = {}
            for z, p in zones.items():
                roi = np.zeros_like(mask)
                cv2.fillPoly(roi, [np.array([[x*width,y*height] for x,y in p], np.int32)], 1)
                scores[z] = float((roi & mask).sum()) / area
            best = max(scores, key=scores.get)
            if scores[best] >= threshold:
                counts[best] += 1
    return counts
