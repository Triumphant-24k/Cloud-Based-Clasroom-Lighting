def decide(occupied, ambient, config, mapping):
    brightness = config['bright_brightness'] if ambient >= config['bright_threshold'] else config['moderate_brightness'] if ambient >= config['moderate_threshold'] else config['dark_brightness']
    return {light: brightness if occupied.get(zone, False) else 0 for zone, light in mapping.items()}

class LightingController:
    def __init__(self, config, mapping):
        self.config, self.mapping, self.mode = config, mapping, 'AUTO'
        self.manual = dict.fromkeys(mapping.values(), 0)

    def calculate(self, occupied, ambient):
        return self.manual.copy() if self.mode == 'MANUAL' else decide(occupied, ambient, self.config, self.mapping)
