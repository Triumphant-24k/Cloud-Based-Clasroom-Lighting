"""Shared local fallback and AWS Lambda decision engine."""
def decide(occupied, ambient, config, mapping):
    brightness = config['bright_brightness'] if ambient >= config['bright_threshold'] else config['moderate_brightness'] if ambient >= config['moderate_threshold'] else config['dark_brightness']
    return {light: brightness if occupied.get(zone, False) else 0 for zone, light in mapping.items()}
