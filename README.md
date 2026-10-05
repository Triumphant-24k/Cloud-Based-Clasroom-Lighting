# Cloud-Based Zone-Based Smart Classroom Lighting System Using Computer Vision

ZoneLight detects anonymous people, maps their bounding-box foot points into six configurable polygons, smooths occupancy, and controls only the corresponding lights. No face recognition, identity, or seat tracking. The repository's original MIT license and Git settings are preserved.

## Quick start (Python 3.11–3.12, Node 20.19+ or 22.12+)

From the repository root, in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. API documentation: http://127.0.0.1:8000/docs. pnpm can substitute for npm. Linux/macOS: use `python3 -m venv .venv` and `.venv/bin/python`.

The default SIMULATION + LOCAL_DEMO + ESP32_SIMULATED setup needs no camera or Azure account. Click scenarios and wait one second for zone ON; empty zones switch OFF after five seconds. Switch lighting to MANUAL for independent sliders, then AUTO to recalculate immediately.

Upload JPG/PNG or MP4/AVI/MOV/MKV for real YOLO detection. The first detection downloads `yolov8n.pt`; internet is required once, or put pretrained weights in the repository and change `yolo_model`. Start Camera uses configured `camera_id`. Raw video remains local. Uploads and history are ignored by Git. Only the device connection string, function URL/key, and ESP32 URL belong in `.env` (copy `.env.example`). Never commit secrets.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
cd frontend
npm run build
```

Configuration lives in `config/`. Restart after edits. All important settings include model, confidence, camera, dimensions, frame sampling, smoothing delays, assignment method (`foot_point` or `overlap`), daylight thresholds, brightness, wattage, cloud and hardware modes. Ambient lux is a demo input by default, not measured illumination. Power uses proportional PWM estimates and saved Wh integrates power savings over runtime; no meter is connected. Pausing freezes occupancy; Reset clears it immediately. Stopping the camera returns to empty simulation and follows the OFF delay. Uploaded videos loop; still images are re-evaluated for smoothing.

See [architecture](docs/architecture.md), [vision](docs/computer_vision.md), [calibration](docs/zone_calibration.md), [cloud](docs/cloud.md), [hardware](docs/hardware.md), and [demo guide](docs/demo-guide.md).

## Scope of validation

Simulation, APIs, history, smoothing, energy calculations, WebSocket updates and build are automated. Real Azure requires your deployment and credentials; real camera and ESP32 require accessible hardware. Firmware is an example for Arduino ESP32 3.x and ArduinoJson 7, and must be compiled/flashed with your board configuration. YOLO accuracy depends on camera view, occlusion, confidence and calibrated polygons. Review Ultralytics licensing before commercial distribution: https://www.ultralytics.com/license.
