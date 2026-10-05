import json
import sqlite3
from backend.config import ROOT

class History:
    def __init__(self):
        (ROOT/'data').mkdir(exist_ok=True)
        self.db = sqlite3.connect(ROOT/'data/history.sqlite3', check_same_thread=False)
        self.db.execute('CREATE TABLE IF NOT EXISTS telemetry (id INTEGER PRIMARY KEY, timestamp TEXT, payload TEXT)')

    def save(self, state):
        self.db.execute('INSERT INTO telemetry(timestamp,payload) VALUES (?,?)',(state['timestamp'],json.dumps(state)))
        self.db.commit()

    def read(self, limit=120):
        return [json.loads(r[0]) for r in reversed(self.db.execute('SELECT payload FROM telemetry ORDER BY id DESC LIMIT ?', (limit,)).fetchall())]
