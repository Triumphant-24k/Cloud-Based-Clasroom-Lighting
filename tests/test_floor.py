import cv2
import numpy as np
import pytest
from backend.cv.zone_mapper import floor_zones, assign_people
from backend.config import ZONES
from fastapi.testclient import TestClient
from backend.main import app

def test_perspective_floor_cells():
    corners = [[.35,.2],[.65,.2],[.95,.95],[.05,.95]]
    zones = floor_zones(corners)
    assert list(zones) == ZONES
    matrix = cv2.getPerspectiveTransform(np.float32([[0,0],[1,0],[1,1],[0,1]]), np.float32(corners))
    for row in range(3):
        for col in range(2):
            x,y = cv2.perspectiveTransform(np.float32([[[(col+.5)/2,(row+.5)/3]]]),matrix)[0,0]*[960,540]
            counts = assign_people([[x-5,y-30,x+5,y]],zones,960,540)
            assert counts[ZONES[row*2+col]] == 1 and sum(counts.values()) == 1
    assert np.allclose(zones['FRONT_LEFT'][2], zones['MIDDLE_RIGHT'][0])

@pytest.mark.parametrize('corners', [[[0,0]]*4, [[0,0],[1,1],[1,0],[0,1]], [[-1,0],[1,0],[1,1],[0,1]], [[0,0],[1,0],[1,1]]])
def test_invalid_floor(corners):
    with pytest.raises(ValueError): floor_zones(corners)

def test_floor_api_is_image_scoped(monkeypatch):
    from backend.cv.detector import PersonDetector
    monkeypatch.setattr(PersonDetector,'detect',lambda self,frame:([[460,200,500,270]],5))
    _,png=cv2.imencode('.png',np.zeros((540,960,3),np.uint8))
    with TestClient(app) as client:
        assert client.post('/api/floor',json={'corners':[[0,0],[1,0],[1,1],[0,1]]}).status_code == 409
        client.post('/api/upload',files={'file':('test.png',png.tobytes(),'image/png')})
        r=client.post('/api/floor',json={'corners':[[.3,.1],[.7,.1],[1,1],[0,1]]})
        assert r.status_code == 200
        assert len(r.json()['floorCorners']) == 4 and not r.json()['detectionRunning']
        assert client.post('/api/floor',json={'corners':[[0,0]]*4}).status_code == 400
        r=client.post('/api/upload',files={'file':('next.png',png.tobytes(),'image/png')})
        assert r.json()['state']['floorCorners'] == []
