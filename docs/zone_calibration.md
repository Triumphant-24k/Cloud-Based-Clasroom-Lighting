# Zone calibration

Stop the backend, then run:

```powershell
.\.venv\Scripts\python.exe -m tools.calibrate --image classroom.jpg
# Or on a working webcam:
.\.venv\Scripts\python.exe -m tools.calibrate --camera 0
```

Click three or more vertices in perimeter order for the named zone. Enter assigns and advances; Backspace removes the last point; Escape cancels without saving. All six names are presented in order. The utility saves only when all six are complete. Restart the backend. Coordinates are normalized 0–1, allowing resized frames. Use polygons representing floor/foot locations, avoid overlaps and self intersections. OpenCV GUI requires `opencv-python`, installed by Ultralytics; headless-only environments cannot use this click utility.
