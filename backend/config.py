import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZONES = ['FRONT_LEFT', 'FRONT_RIGHT', 'MIDDLE_LEFT', 'MIDDLE_RIGHT', 'BACK_LEFT', 'BACK_RIGHT']

def load_config():
    settings = json.loads((ROOT / 'config/system_config.json').read_text())
    zones = json.loads((ROOT / 'config/classroom_zones.json').read_text())
    mapping = json.loads((ROOT / 'config/light_mapping.json').read_text())
    if set(zones) != set(ZONES) or set(mapping) != set(ZONES):
        raise ValueError('Configuration must define all six zones')
    if len(set(mapping.values())) != 6:
        raise ValueError('Each zone must map to an independent light')
    for polygon in zones.values():
        if len(polygon) < 3 or any(len(p) != 2 or not all(0 <= n <= 1 for n in p) for p in polygon):
            raise ValueError('Polygons need at least three normalized points')
    if min(settings['zone_on_delay'], settings['zone_off_delay'], settings['light_wattage']) < 0:
        raise ValueError('Delays and wattage must be nonnegative')
    return settings, zones, mapping
