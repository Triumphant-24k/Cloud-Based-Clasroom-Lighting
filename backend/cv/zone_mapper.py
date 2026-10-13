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


def floor_zones(corners):
    """Project a 2-column, 3-row rectangular floor into an image.

    Corners: front-left, front-right, back-right, back-left (board at front).
    Requires a planar rectangular classroom and user-calibrated corners.
    """
    points = np.asarray(corners, dtype=np.float32)
    if points.shape != (4, 2) or not np.isfinite(points).all() or ((points < 0) | (points > 1)).any():
        raise ValueError('Select four corners inside the image')
    contour = points.reshape(-1, 1, 2)
    if not cv2.isContourConvex(contour) or abs(cv2.contourArea(contour)) < .01:
        raise ValueError('Floor corners must form a convex boundary with a useful area')
    transform = cv2.getPerspectiveTransform(np.float32([[0,0],[1,0],[1,1],[0,1]]), points)
    result = {}
    for row, name in enumerate(('FRONT', 'MIDDLE', 'BACK')):
        for col, side in enumerate(('LEFT', 'RIGHT')):
            x, y = col / 2, row / 3
            cell = np.float32([[[x,y],[x+.5,y],[x+.5,y+1/3],[x,y+1/3]]])
            result[name+'_'+side] = cv2.perspectiveTransform(cell, transform)[0].tolist()
    return result
