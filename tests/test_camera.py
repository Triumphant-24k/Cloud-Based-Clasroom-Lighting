from types import SimpleNamespace
import numpy as np
import pytest
import backend.cv.camera as camera

@pytest.mark.parametrize('windows',[True,False])
def test_live_capture_backend_and_warmup(monkeypatch,windows):
    frame=np.zeros((4,6,3),dtype=np.uint8);reads=iter([(False,None),(True,frame),(True,frame)])
    capture=SimpleNamespace(isOpened=lambda:True,set=lambda *args:None,read=lambda:next(reads),release=lambda:None)
    opens=[]
    monkeypatch.setattr(camera,'os',SimpleNamespace(name='nt' if windows else 'posix'))
    monkeypatch.setattr(camera.cv2,'VideoCapture',lambda *args:opens.append(args) or capture)
    monkeypatch.setattr(camera.time,'sleep',lambda _:None)
    source=camera.CameraSource();source.open('LIVE_CAMERA',1,{'frame_width':6,'frame_height':4})
    assert opens==[(1,camera.cv2.CAP_DSHOW)] if windows else opens==[(1,)]
    assert source.read() is frame
    assert source.read() is frame
    source.close()


def test_open_without_frames_releases_camera(monkeypatch):
    released=[]
    capture=SimpleNamespace(isOpened=lambda:True,set=lambda *args:None,read=lambda:(False,None),release=lambda:released.append(True))
    monkeypatch.setattr(camera.cv2,'VideoCapture',lambda *args:capture)
    monkeypatch.setattr(camera.time,'sleep',lambda _:None)
    source=camera.CameraSource()
    with pytest.raises(ValueError,match='no frames'):
        source.open('LIVE_CAMERA',1,{'frame_width':6,'frame_height':4})
    assert released and source.capture is None


def test_switching_to_phone_clears_old_simulated_occupancy(monkeypatch):
    from fastapi.testclient import TestClient
    import backend.main as main
    from backend.cv.detector import PersonDetector
    monkeypatch.setattr(camera.CameraSource,'open',lambda *args:None)
    monkeypatch.setattr(camera.CameraSource,'read',lambda self:np.zeros((540,960,3),dtype=np.uint8))
    monkeypatch.setattr(PersonDetector,'detect',lambda *args:([],0))
    with TestClient(main.app) as client:
        main.engine.smoother.state=dict.fromkeys(main.ZONES,True)
        response=client.post('/api/control',json={'action':'camera'})
        state=response.json()
        assert response.status_code==200 and state['sourceMode']=='LIVE_CAMERA'
        assert state['peopleDetected']==0 and state['occupiedZoneCount']==0
        assert all(value==0 for value in state['lights'].values())
