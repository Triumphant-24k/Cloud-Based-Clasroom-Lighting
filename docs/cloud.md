# AWS cloud vision

The `zonelight-classroom` stack in `ap-southeast-2` runs YOLOv8n person detection, calibrated floor homography, zone assignment, relative image brightness and lighting decisions in the same ARM64 Python 3.12 Lambda. DynamoDB stores count, classroomId, timestamp, classTime, occupiedZones, zoneCounts, model, computeLocation and lighting. IoT publishes telemetry/automatic commands. The laptop captures/resizes JPEGs, signs requests, draws the returned geometry/boxes and runs the dashboard. The ESP32 currently remains simulated; the firmware's local HTTP bridge can receive real outputs later.

The default mode is CLOUD_CONNECTED. Uploaded photos are analyzed once and paused. Applying floor calibration makes one additional request. Camera/video cloud analysis is limited to once every 10 seconds. Floor corners are selected by the user; cloud computation does not infer an accurate hidden floor automatically. A rectangular, planar floor is assumed, and bottom-centre bounding boxes estimate student floor position. Counts and brightness are estimates, not certified attendance or calibrated lux.

Images are sent to the IAM-authenticated HTTPS Function URL for computation. Images, pixel payloads and face identities are never written to DynamoDB, S3 or logs. The private encrypted S3 bucket contains code/model deployment ZIPs only. Lambda logs contain anonymous counts, request IDs and record IDs. CloudWatch retention is seven days; history has asynchronous seven-day DynamoDB TTL. Both history and deployment artifacts are retained on stack deletion.

## Deploy

Use profile zonelight and the selected Region ap-southeast-2. Do not upgrade the Free plan. AWS Settings > Billing shows credits; verify Region at AWS Settings > View all projects > Overview > Additional Info > Region. The existing credit safeguard stops cloud requests below the original $100 spend budget, but billing reporting can lag.

`cloud/template.yaml` is the source. `tools.package_vision` builds the Lambda ZIP and generates `cloud/vision-deployment-template.json` with the S3 CodeUri. Do not use the retired inline `tools.package_aws` workflow: it cannot package model dependencies. No Docker, ECR, GPU, provisioned concurrency, VPC or always-running instance is required.

Export existing yolov8n.pt to ONNX with Ultralytics: format=onnx, opset=12, simplify=False, imgsz=640, dynamic=False. Copy to cloud/yolov8n.onnx; copy config/classroom_zones.json to cloud/classroom_zones.json. Download pinned wheels from cloud/requirements-vision.txt for Python 3.12 ARM64 Linux: numpy/OpenCV manylinux2014_aarch64 and Pillow manylinux_2_28_aarch64. Package with `python -m tools.package_vision --wheels <wheel-directory> --bucket <ArtifactBucketName-output> --key vision/<unique-version>.zip --output <zip-path>`. Upload the ZIP to that bucket/key. Run cfn-lint and cfn-guard on the generated template. Deploy with AWS CLI cloudformation deploy, stack zonelight-classroom, CAPABILITY_IAM, ClassroomId=CLASSROOM-01, FunctionConcurrency=2, profile zonelight, region ap-southeast-2. Use a unique S3 key for every code update. .env retains the existing Function URL and credentials stay outside the frontend.

The same Lambda/function URL and existing history table are preserved. CPU model inference uses 2048 MB memory, timeout 60 seconds, reserved concurrency two, compressed JPEG payloads and no stored images. The package includes only CPU OpenCV DNN, NumPy, Pillow and the exported model, avoiding PyTorch's large runtime.

## Proof and failure handling

The webpage's AWS implementation proof includes computeLocation=AWS_LAMBDA, model, requestId and recordId. Match the recordId to DynamoDB and the requestId to the cloud_vision_complete log. Function code is packaged as a ZIP larger than the console editor supports; source is in cloud/vision.py, cloud/vision_handler.py and cloud/decision.py.

AWS mode never silently runs local person detection. On cloud failure the source pauses and reports CLOUD OFFLINE / VISION PAUSED. LOCAL_DEMO can explicitly run local inference or simulation. The last successful cloud receipt stays identified as the last analysis; it is not a new inference on each preview refresh.

To pause: stop the local backend/frontend and set FunctionConcurrency=0 through a stack update, or set Lambda reserved concurrency zero directly as a temporary emergency shutoff. Restore two to resume. Inspect get-function-concurrency because an emergency direct update introduces drift from the template. Small storage charges may remain while paused.
