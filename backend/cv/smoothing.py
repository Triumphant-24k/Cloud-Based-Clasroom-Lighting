class OccupancySmoother:
    def __init__(self, zones, on_delay=1, off_delay=5):
        self.state = dict.fromkeys(zones, False)
        self.pending = {}
        self.on_delay, self.off_delay = on_delay, off_delay

    def update(self, raw, now):
        for zone in self.state:
            target = bool(raw.get(zone, False))
            if target == self.state[zone]:
                self.pending.pop(zone, None)
                continue
            if zone not in self.pending or self.pending[zone][0] != target:
                self.pending[zone] = (target, now)
            delay = self.on_delay if target else self.off_delay
            if now - self.pending[zone][1] >= delay:
                self.state[zone] = target
                del self.pending[zone]
        return self.state.copy()
