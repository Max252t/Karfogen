import threading
import time


VOLATILE_TYPES = frozenset(["status", "slice_progress"])


class EventBus(object):
    MAX_EVENTS = 1000

    def __init__(self):
        self._cond = threading.Condition(threading.Lock())
        self._events = []
        self._last_id = 0
        self.revision = 0

    def _repeats_last(self, event_type, data):
        if event_type not in VOLATILE_TYPES:
            return False
        for event in reversed(self._events):
            if event["type"] == event_type:
                return event["data"] == data
        return False

    def _trim(self):
        while len(self._events) > self.MAX_EVENTS:
            index = 0
            for position, item in enumerate(self._events):
                if item["type"] in VOLATILE_TYPES:
                    index = position
                    break
            del self._events[index]

    def publish(self, event_type, data=None):
        with self._cond:
            data = data if data is not None else {}
            if self._repeats_last(event_type, data):
                return self._events[-1]
            self._last_id += 1
            event = {
                "id": self._last_id,
                "ts": time.time(),
                "type": event_type,
                "data": data,
            }
            self._events.append(event)
            self._trim()
            self._cond.notify_all()
            return event

    def get_since(self, since=0, wait=0.0):
        deadline = time.time() + wait
        with self._cond:
            while True:
                result = [e for e in self._events if e["id"] > since]
                if result or wait <= 0:
                    return {"events": result, "last": self._last_id}
                remaining = deadline - time.time()
                if remaining <= 0:
                    return {"events": [], "last": self._last_id}
                self._cond.wait(remaining)

    def clear(self):
        with self._cond:
            self._events = []
            self.revision += 1

    def snapshot(self):
        with self._cond:
            return list(self._events)

    def read(self, revision, since):
        with self._cond:
            if revision != self.revision:
                return self.revision, True, list(self._events)
            return self.revision, False, [e for e in self._events if e["id"] > since]

    def load(self, events):
        with self._cond:
            self._events = list(events)
            self._trim()
            highest = max([e["id"] for e in self._events] or [0])
            self._last_id = max(self._last_id, highest)
            self.revision += 1
            self._cond.notify_all()


_bus = EventBus()


def get_bus():
    return _bus
