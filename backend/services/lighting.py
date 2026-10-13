from cloud.decision import decide

class LightingController:
    def __init__(self, config, mapping):
        self.config, self.mapping, self.mode = config, mapping, 'AUTO'
        self.manual = dict.fromkeys(mapping.values(), 0)

    def calculate(self, occupied, ambient):
        return self.manual.copy() if self.mode == 'MANUAL' else decide(occupied, ambient, self.config, self.mapping)
