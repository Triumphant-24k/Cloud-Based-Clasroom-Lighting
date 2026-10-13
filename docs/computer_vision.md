# Computer vision

`PersonDetector` lazily loads configurable Ultralytics weights and predicts only `classes=[0]` (COCO person). No face processing or identity tracking. Foot point is `((x1+x2)/2, y2)` normalized by frame dimensions. Polygon tests include boundaries; at a shared edge the first configured polygon wins, preventing double counting. Overlap mode assigns the largest polygon intersection divided by bounding-box area if above `overlap_threshold`.

Default polygons form a two-column, three-row grid as a demo only. Calibrate perspective ROIs for the real classroom. Camera angle, seated bodies, occlusion and dropped detections affect accuracy. Adjust confidence and camera placement. ON requires continuous positive evidence for one second; OFF requires continuous absence for five seconds. Evidence reversal clears the pending transition. FPS reflects the processing loop; inference latency measures YOLO prediction, not network delivery.

The synthetic sample clip contains desks, not photographic people. It validates decoding, overlays and video looping, and is not an accuracy benchmark. Scenario mode generates anonymous simulated detections. Use consented classroom footage to evaluate real-world precision/recall. Source: https://docs.ultralytics.com/modes/predict/.

## Phone Link camera

This laptop uses Phone Link camera input 1 (1280x720). The built-in HP camera is input 0. Windows live capture uses OpenCV DirectShow; Media Foundation opens these devices but did not deliver frames during verification. Keep Use as connected camera enabled and allow Link to Windows camera permissions. Close Windows Camera/Teams before starting detection. Camera indices may change after reconnecting; adjust camera_id in config/system_config.json if needed.

Click Start Camera in the local dashboard. YOLO detects visible people locally; six fixed polygons assign their positions to zones. AWS receives only anonymous counts, zone occupancy and relative image brightness, computes LED levels, and stores classroom/time/count records. This does not distinguish students from teachers, identify people, or determine exact seat numbers. For a fixed elevated phone view, calibrate the six polygons using tools.calibrate --camera 1 so image perspective matches the actual classroom zones.
