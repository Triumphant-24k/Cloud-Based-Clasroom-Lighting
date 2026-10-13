# ESP32 integration: ready before the board arrives

## Connection path
Phone/uploaded image -> AWS Lambda detects people and computes six light levels -> laptop backend forwards the result over local Wi-Fi -> ESP32 drives six LEDs with PWM. The AWS request ID accompanies the device command so the webpage can show which cloud result was acknowledged. The ESP32 does not need AWS keys, certificates or a paid service. It uses the existing laptop bridge, so the laptop must remain running.

## Prepared files
Your actual Arduino sketch is:
`C:/Users/Trium/OneDrive/Desktop/IMP/Cloud-Based-Clasroom-Lighting/firmware/esp32_lighting/esp32_lighting.ino`

Its local `secrets.h` was generated with a device key matching the backend's ignored `.env`. Open `secrets.h` in Arduino IDE and replace YOUR_WIFI_SSID and YOUR_WIFI_PASSWORD with your 2.4 GHz Wi-Fi credentials before flashing. Keep the generated device token unchanged. Neither file should be committed, shared in your report or shown to the teacher. The source ZIP contains only a credentials example, not your generated secret file.

Firmware uses Arduino-ESP32 3.x and ArduinoJson 7. ArduinoJson 7.4.3 is already installed. The sketch targets a **classic ESP32 Dev Module / ESP32-WROOM development board**. Before uploading, confirm the board model. ESP32-C3/S3 boards need different pin mappings; the sketch intentionally rejects those targets rather than using inappropriate GPIOs.

## Wire the six LEDs when the board arrives
Use ordinary low-current indicator LEDs. Wire each GPIO -> 330 ohm resistor -> LED anode (long leg), then LED cathode (short leg/flat side) -> GND. Each LED needs its own resistor. Connect all ground wires to the ESP32 GND. Power the development board by USB. Do not connect large lamps or strips directly to these pins.

| Zone | Output | GPIO |
|---|---|---:|
| Front left | LIGHT_1 | 13 |
| Front right | LIGHT_2 | 14 |
| Middle left | LIGHT_3 | 25 |
| Middle right | LIGHT_4 | 26 |
| Back left | LIGHT_5 | 27 |
| Back right | LIGHT_6 | 32 |

## Upload and connect
1. Connect the ESP32 with a USB data cable. Open the actual sketch above in Arduino IDE.
2. Set your Wi-Fi name and password in its `secrets.h` tab. Laptop and board must be on the same trusted Wi-Fi; guest/campus networks that isolate clients will block the connection. A private router or phone hotspot with client-to-client access works. ESP32 Wi-Fi uses 2.4 GHz.
3. Select Tools > Board > ESP32 Arduino > ESP32 Dev Module for the classic board. Select its COM port. Click Verify, then Upload. If your exact board differs, confirm its model before choosing pins or uploading.
4. Open Serial Monitor at **115200 baud**. Copy the printed **ESP32 IP**. If no COM port appears, check the data cable and the board's USB driver; the required driver depends on the actual board.
5. Start the local webpage/backend. In its **ESP32 connection** panel, enter that IP and click **Connect ESP32**. The server verifies matching firmware and device key before enabling real-device mode. You should see **ESP32 CONNECTED · COMMAND ACKNOWLEDGED**.
6. First use MANUAL and move each slider from 0 to 100 to verify the corresponding LED. Then use AUTO, AWS cloud and upload a classroom photo. The returned cloud light levels are forwarded to the board. Show the firmware acknowledgement and matching AWS request ID on the webpage.

AWS Lambda is currently paused (reserved concurrency zero). Local/manual LED tests do not need AWS. Restore Lambda concurrency two only when doing cloud image/camera analysis. No paid plan upgrade is needed.

## Behavior and shutdown
The laptop sends a local heartbeat approximately once per second, including while a still image is paused. This does not repeat AWS inference. The ESP32 holds the same six PWM levels while the backend is available. **Disconnect & turn LEDs off** immediately requests all six outputs off. When the server is killed or Wi-Fi is lost, the firmware turns LEDs off after 30 seconds without a command. On AWS vision failure in AUTO, the backend sends zero light levels instead of holding stale results.

The firmware validates all six values before applying any, uses a local device key, and acknowledges the command ID plus applied levels. The acknowledgement proves firmware accepted PWM values; actual LED illumination still requires physical testing. The device API uses HTTP on private Wi-Fi, so do not expose it through router port forwarding or use an untrusted shared network. AWS credentials stay only on the laptop.

## Still required after arrival
Confirm the exact board, wire the LEDs, enter Wi-Fi credentials, flash the sketch, read its IP, and verify physical brightness. These cannot be completed without the board.

## Verified before the board arrives

- Firmware compiled successfully for `esp32:esp32:esp32` with Arduino-ESP32 3.3.2 and ArduinoJson 7.4.3.
- Sketch uses 951967 bytes of flash; globals use 45336 bytes of RAM.
- All 67 server tests passed, including authenticated connection, six-value acknowledgements, disconnect shutdown and zero brightness on cloud vision failure.
- Frontend production build passed.
- Firmware and server device keys match. The downloadable ZIP excludes the generated secret header.
- Flashing, actual Wi-Fi connection and physical LED brightness checks remain pending until the board arrives.
