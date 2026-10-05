# Demo guide

1. Start backend and frontend as in README. Simulation starts with scattered occupants.
2. Click Empty Classroom and wait five seconds: all six outputs turn off.
3. Front Row Only: after one second LIGHT_1 and LIGHT_2 turn on. Middle/Back scenarios exercise other pairs.
4. Bright Daylight gives occupied zones 30%, Cloudy Classroom 60%, Night Mode 100%.
5. Full Classroom at night uses estimated 240 W; three occupied zones at cloudy ambient use 72 W and save 70% against full lighting.
6. Select MANUAL and adjust each slider. Select AUTO to immediately apply current occupancy and ambient.
7. Simulate Cloud Failure: dashboard shows CLOUD OFFLINE and LOCAL FALLBACK ACTIVE; occupancy/light decisions continue. Restore Cloud recovers.
8. Upload an actual classroom image or video. First YOLO use may download weights. People boxes and foot points map to calibrated zones. Sample Video is synthetic and demonstrates file decoding only.
9. On a working laptop choose Start Camera. If unavailable, the API returns an actionable error and simulation remains usable.
10. Inspect analytics, estimated cumulative energy, events, and API docs. Reset clears occupancy and returns to empty simulation.

Do not present simulated ambient light, synthetic persons, simulated cloud/device, or estimated watts as physical measurements. Real Azure and hardware need separately provisioned resources. Test on recorded footage before relying on control in a classroom.
