# Computer vision

`PersonDetector` lazily loads configurable Ultralytics weights and predicts only `classes=[0]` (COCO person). No face processing or identity tracking. Foot point is `((x1+x2)/2, y2)` normalized by frame dimensions. Polygon tests include boundaries; at a shared edge the first configured polygon wins, preventing double counting. Overlap mode assigns the largest polygon intersection divided by bounding-box area if above `overlap_threshold`.

Default polygons form a two-column, three-row grid as a demo only. Calibrate perspective ROIs for the real classroom. Camera angle, seated bodies, occlusion and dropped detections affect accuracy. Adjust confidence and camera placement. ON requires continuous positive evidence for one second; OFF requires continuous absence for five seconds. Evidence reversal clears the pending transition. FPS reflects the processing loop; inference latency measures YOLO prediction, not network delivery.

The synthetic sample clip contains desks, not photographic people. It validates decoding, overlays and video looping, and is not an accuracy benchmark. Scenario mode generates anonymous simulated detections. Use consented classroom footage to evaluate real-world precision/recall. Source: https://docs.ultralytics.com/modes/predict/.
