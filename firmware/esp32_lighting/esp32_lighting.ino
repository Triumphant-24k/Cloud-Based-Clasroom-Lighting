// ZoneLight: classic ESP32 Dev Module, Arduino-ESP32 3.x, ArduinoJson 7.
// AWS computes results; the laptop forwards them over private Wi-Fi.
#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoJson.h>
#include "secrets.h"

#if !defined(CONFIG_IDF_TARGET_ESP32)
#error "This pin layout is for a classic ESP32. Confirm the board model before adapting it."
#endif

const int LIGHT_PINS[6] = {13, 14, 25, 26, 27, 32};
const char* ZONE_NAMES[6] = {"FRONT_LEFT", "FRONT_RIGHT", "MIDDLE_LEFT", "MIDDLE_RIGHT", "BACK_LEFT", "BACK_RIGHT"};
const uint32_t COMMAND_TIMEOUT_MS = 30000;
const char* HEADER_NAMES[] = {"X-ZoneLight-Token"};
WebServer server(80);
int levels[6] = {0};
bool occupied[6] = {false};
bool pwmReady = true, hasCommand = false, timedOut = false, wifiReported = false;
uint32_t lastCommand = 0, lastReconnect = 0;
String lastCommandId, lastCloudRequestId;

bool applyLevels() {
  bool success = true;
  for (int i = 0; i < 6; ++i) if (!ledcWrite(LIGHT_PINS[i], map(levels[i], 0, 100, 0, 255))) success = false;
  return success;
}

bool authorized() {
  if (server.header("X-ZoneLight-Token") != ZONELIGHT_DEVICE_TOKEN) {
    server.send(403, "application/json", "{\"error\":\"Device key mismatch\"}");
    return false;
  }
  return true;
}

void replyStatus(bool acknowledgement) {
  JsonDocument doc;
  doc["device"] = "ZoneLight-ESP32";
  doc["protocol"] = 1;
  doc["pwmReady"] = pwmReady;
  doc["ip"] = WiFi.localIP().toString();
  doc["uptimeMs"] = millis();
  doc["stale"] = !hasCommand || timedOut;
  doc["commandId"] = lastCommandId;
  doc["cloudRequestId"] = lastCloudRequestId;
  if (acknowledgement) doc["ok"] = true;
  for (int i = 0; i < 6; ++i) {
    doc["lights"]["LIGHT_" + String(i + 1)] = levels[i];
    doc["occupiedZones"][ZONE_NAMES[i]] = occupied[i];
  }
  String response;
  serializeJson(doc, response);
  server.send(200, "application/json", response);
}

void receiveLights() {
  if (!authorized()) return;
  if (!pwmReady) { server.send(503, "application/json", "{\"error\":\"PWM setup failed\"}"); return; }
  String body = server.arg("plain");
  if (body.length() > 4096) { server.send(413, "application/json", "{\"error\":\"Command too large\"}"); return; }
  JsonDocument doc;
  if (deserializeJson(doc, body)) { server.send(400, "application/json", "{\"error\":\"Invalid JSON\"}"); return; }
  JsonObjectConst lights = doc["lights"].as<JsonObjectConst>();
  if (lights.isNull() || lights.size() != 6 || !doc["commandId"].is<const char*>()) {
    server.send(400, "application/json", "{\"error\":\"Six lights and a command ID are required\"}"); return;
  }
  String commandId = doc["commandId"].as<String>();
  if (!commandId.length() || commandId.length() > 64) {
    server.send(400, "application/json", "{\"error\":\"Invalid command ID\"}"); return;
  }
  int nextLevels[6];
  for (int i = 0; i < 6; ++i) {
    String key = "LIGHT_" + String(i + 1);
    if (!lights[key].is<int>() || lights[key].as<int>() < 0 || lights[key].as<int>() > 100) {
      server.send(400, "application/json", "{\"error\":\"Each brightness must be an integer 0-100\"}"); return;
    }
    nextLevels[i] = lights[key].as<int>();
  }
  // Apply only after every value has passed validation.
  for (int i = 0; i < 6; ++i) {
    levels[i] = nextLevels[i];
    occupied[i] = doc["occupiedZones"][ZONE_NAMES[i]] | false;
  }
  lastCommandId = commandId;
  lastCloudRequestId = doc["cloudRequestId"] | "";
  lastCommand = millis(); hasCommand = true; timedOut = false;
  if (!applyLevels()) {
    pwmReady = false;
    server.send(503, "application/json", "{\"error\":\"PWM write failed\"}"); return;
  }
  replyStatus(true);
}

void setup() {
  Serial.begin(115200);
  for (int pin : LIGHT_PINS) if (!ledcAttach(pin, 5000, 8)) pwmReady = false;
  if (!applyLevels()) pwmReady = false; // Start with all six outputs off.
  Serial.println("ZoneLight ESP32 starting; all LEDs OFF.");
  if (!pwmReady) Serial.println("PWM setup failed. Check selected board and pin layout.");
  server.collectHeaders(HEADER_NAMES, 1);
  server.on("/lights", HTTP_POST, receiveLights);
  server.on("/status", HTTP_GET, []() { if (authorized()) replyStatus(false); });
  server.onNotFound([]() { server.send(404, "application/json", "{\"error\":\"Not found\"}"); });
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(ZONELIGHT_WIFI_SSID, ZONELIGHT_WIFI_PASSWORD);
  server.begin();
  Serial.println("Connecting to 2.4 GHz Wi-Fi. Edit secrets.h before uploading.");
}

void loop() {
  server.handleClient();
  if (WiFi.status() == WL_CONNECTED) {
    if (!wifiReported) {
      Serial.print("ESP32 IP: "); Serial.println(WiFi.localIP());
      Serial.println("Enter this IP in the webpage's ESP32 connection panel.");
      wifiReported = true;
    }
  } else {
    wifiReported = false;
    if (millis() - lastReconnect > 10000) {
      lastReconnect = millis(); WiFi.reconnect();
      Serial.println("Wi-Fi disconnected; reconnecting.");
    }
  }
  if (hasCommand && !timedOut && millis() - lastCommand > COMMAND_TIMEOUT_MS) {
    for (int i = 0; i < 6; ++i) { levels[i] = 0; occupied[i] = false; }
    applyLevels(); timedOut = true;
    Serial.println("No server heartbeat for 30 seconds; LEDs OFF.");
  }
  delay(5);
}
