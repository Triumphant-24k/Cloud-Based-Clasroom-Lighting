class EnergyTracker:
    def __init__(self, wattage, light_count=6):
        self.wattage, self.baseline = wattage, wattage*light_count
        self.saved_wh, self.last, self.previous_saved = 0.0, None, 0.0

    def update(self, brightness, now):
        power = sum(brightness.values())/100*self.wattage
        saved = self.baseline-power
        if self.last is not None:
            self.saved_wh += self.previous_saved*max(0,now-self.last)/3600
        self.last, self.previous_saved = now, saved
        return {'baselinePower':self.baseline,'smartPower':power,'powerSaved':saved,'savingPercentage':100*saved/self.baseline if self.baseline else 0,'cumulativeEnergySavedWh':self.saved_wh,'estimated':True}
