#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoJson.h>
const char* WIFI_SSID="YOUR_WIFI_SSID";
const char* WIFI_PASSWORD="YOUR_WIFI_PASSWORD";
const int pins[6]={13,14,25,26,27,32};
const char* zones[6]={"FRONT_LEFT","FRONT_RIGHT","MIDDLE_LEFT","MIDDLE_RIGHT","BACK_LEFT","BACK_RIGHT"};
bool occupied[6]={false};
int levels[6]={0};
unsigned long lastCommand=0,lastReconnect=0;
bool useLDR=false; // optional ADC on GPIO34; calibrate to lux before enabling
int ambient=450;
WebServer server(80);
void apply(){for(int i=0;i<6;i++)ledcWrite(pins[i],map(levels[i],0,100,0,255));}
void setup(){
 Serial.begin(115200);
 for(int pin:pins)ledcAttach(pin,5000,8);
 apply();WiFi.begin(WIFI_SSID,WIFI_PASSWORD);
 server.on("/lights",HTTP_POST,[](){
  JsonDocument doc;
  if(deserializeJson(doc,server.arg("plain"))){server.send(400,"text/plain","Invalid JSON");return;}
  for(int i=0;i<6;i++){String key="LIGHT_"+String(i+1);if(!doc["lights"][key].is<int>() || doc["lights"][key].as<int>()<0 || doc["lights"][key].as<int>()>100){server.send(400,"text/plain","Need six values 0-100");return;}}
  for(int i=0;i<6;i++){levels[i]=doc["lights"]["LIGHT_"+String(i+1)];occupied[i]=doc["occupiedZones"][zones[i]]|false;}
  ambient=doc["ambientLight"]|450;lastCommand=millis();apply();Serial.println("Lighting command applied");server.send(200,"application/json","{\"ok\":true}");
 });
 server.on("/status",HTTP_GET,[](){JsonDocument doc;doc["uptimeMs"]=millis();doc["fallback"]=millis()-lastCommand>5000;doc["ambientLight"]=ambient;for(int i=0;i<6;i++)doc["lights"]["LIGHT_"+String(i+1)]=levels[i];String result;serializeJson(doc,result);server.send(200,"application/json",result);});
 server.begin();Serial.println("HTTP lighting device ready; check router for IP");
}
void loop(){
 server.handleClient();
 if(WiFi.status()!=WL_CONNECTED && millis()-lastReconnect>10000){lastReconnect=millis();WiFi.reconnect();Serial.println("WiFi reconnecting");}
 if(millis()-lastCommand>5000){
  if(useLDR)ambient=map(analogRead(34),0,4095,0,1000);
  int brightness=ambient>=700?30:ambient>=300?60:100;
  // Hold last occupancy briefly, then switch off when metadata becomes stale.
  for(int i=0;i<6;i++)levels[i]=(millis()-lastCommand<15000 && occupied[i])?brightness:0;
  apply();
 }
 delay(10);
}
