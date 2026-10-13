"""Prepare local firmware credentials without placing secrets in tracked files."""
import json
import secrets
from pathlib import Path
from dotenv import dotenv_values

ROOT=Path(__file__).resolve().parents[1]

def main():
    env=ROOT/'.env'
    values=dotenv_values(env) if env.exists() else {}
    token=values.get('ESP32_TOKEN') or secrets.token_hex(32)
    if len(token)<32:
        raise SystemExit('Existing device key is too short; remove ESP32_TOKEN and run again')
    content=env.read_text(encoding='utf-8') if env.exists() else ''
    if not values.get('ESP32_TOKEN'):
        env.write_text(content.rstrip()+'\nESP32_TOKEN='+token+'\n',encoding='utf-8')
    header=ROOT/'firmware/esp32_lighting/secrets.h'
    if not header.exists():
        header.write_text('#pragma once\n// Local only: do not share or commit this file.\n'
                          '#define ZONELIGHT_WIFI_SSID "YOUR_WIFI_SSID"\n'
                          '#define ZONELIGHT_WIFI_PASSWORD "YOUR_WIFI_PASSWORD"\n'
                          '#define ZONELIGHT_DEVICE_TOKEN '+json.dumps(token)+'\n',encoding='utf-8')
    print('Local device key and firmware secrets.h are ready. Edit only the Wi-Fi name/password in secrets.h.')

if __name__=='__main__': main()
