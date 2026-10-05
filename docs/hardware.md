# ESP32 hardware

Open firmware/esp32_lighting/esp32_lighting.ino in Arduino IDE. Use Espressif Arduino ESP32 3.x and ArduinoJson 7. Set placeholder WiFi credentials locally, select your board, compile and flash. GPIO13/14/25/26/27/32 correspond to LIGHT_1–6 using 5 kHz 8-bit PWM. Use low-voltage LEDs with suitable MOSFET drivers and common ground. PWM is not appropriate for ordinary mechanical relays. Never connect classroom mains lamps directly to GPIO; use rated isolated dimmable drivers and qualified installation.

Find the board's IP from your router and set ESP32_URL in `.env`. Enable ESP32_CONNECTED. Backend POSTs `/lights` with six percentages and occupancy. GET `/status` reports brightness, uptime, ambient and stale-command fallback. Hardware delivery failure is shown separately from cloud failure. Simulated device means desired outputs, not physical actuation feedback.

The device holds last known occupied zones and recalculates locally after five seconds without commands. At 15 seconds stale occupancy is discarded and outputs turn off. It cannot independently detect people. WiFi reconnects every ten seconds. Optional GPIO34 LDR requires calibration; raw ADC mapping is only an illustrative estimate. Synchronize firmware thresholds if configuration changes. Local HTTP is intended for a trusted demo LAN; add authentication/TLS or an isolated network for deployment.

ESP32 LEDC reference: https://docs.espressif.com/projects/arduino-esp32/en/latest/api/ledc.html.
