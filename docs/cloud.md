# Cloud integration

LOCAL_DEMO is a simulated cloud decision engine in the laptop process. CLOUD_CONNECTED sends metadata to a real Azure Function over HTTPS. If `AZURE_IOT_DEVICE_CONNECTION_STRING` is provided, the same metadata is first sent as IoT Hub device telemetry using the asynchronous Azure SDK. The HTTP response is the command path; this project does not claim an IoT Hub routing rule is automatically deployed.

Deploy the `cloud/` folder as a Python Azure Functions v2 application (install Azure Functions Core Tools and Azure CLI yourself; create a Function App with a supported Python runtime). From `cloud`, use `func azure functionapp publish YOUR_FUNCTION_APP`. Copy the function's HTTPS `/api/lighting` URL and function key into `.env`. Create an IoT Hub device identity and copy its device connection string if telemetry ingestion is desired. Set mode to CLOUD_CONNECTED through config or dashboard. No frames, image bytes, names or identifying features are sent.

Payload includes classroomId, timestamp, peopleDetected, occupiedZones, ambientLight and systemMode. Response is `{ "lights": { "LIGHT_1": 60, ... } }`. Set Function App environment settings BRIGHT_THRESHOLD, MODERATE_THRESHOLD and the three *_BRIGHTNESS values to match local config. The cloud function uses fixed standard six-zone mapping; update it if you change light identifiers. Real connected deployments should protect endpoint access, restrict networking, and manage device credentials outside source control.

Three-second API timeout, missing credentials, failed IoT telemetry and malformed commands all activate local fallback. Retry happens on subsequent ticks, restoring cloud automatically. Simulate Cloud Failure reproduces the same decision fallback. Manual mode overrides the automatic cloud result on the laptop. Backend then sends commands to real ESP32 over local HTTP; the ESP32 does not subscribe directly to Azure in this example.

References: https://learn.microsoft.com/python/api/azure-iot-device/azure.iot.device.iothubdeviceclient and https://learn.microsoft.com/azure/azure-functions/functions-reference-python.
