from collections import OrderedDict
from threading import Lock

from app.application.ports import OccupationAnalyzer
from app.domain.occupation import OccupationProfile


class CachedOccupationAnalyzer:
    def __init__(self, analyzer: OccupationAnalyzer, capacity: int) -> None:
        self._analyzer = analyzer
        self._capacity = capacity
        self._readings: OrderedDict[str, OccupationProfile] = OrderedDict()
        self._lock = Lock()

    def analyze(self, occupation: str) -> OccupationProfile:
        with self._lock:
            remembered = self._readings.get(occupation)
            if remembered is not None:
                self._readings.move_to_end(occupation)
                return remembered
        profile = self._analyzer.analyze(occupation)
        with self._lock:
            self._readings[occupation] = profile
            self._readings.move_to_end(occupation)
            while len(self._readings) > self._capacity:
                self._readings.popitem(last=False)
        return profile
