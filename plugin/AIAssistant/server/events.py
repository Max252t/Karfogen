import threading
import time


class EventBus(object):
    MAX_EVENTS = 1000

    def __init__(self):
        self._cond = threading.Condition(threading.Lock())
        self._events = []
        self._last_id = 0

    def publish(self, event_type, data=None):
        with self._cond:
            self._last_id += 1
            event = {
                "id": self._last_id,
                "ts": time.time(),
                "type": event_type,
                "data": data if data is not None else {},
            }
            self._events.append(event)
            if len(self._events) > self.MAX_EVENTS:
                del self._events[:len(self._events) - self.MAX_EVENTS]
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

    def snapshot(self):
        with self._cond:
            return list(self._events)

    def load(self, events):
        with self._cond:
            self._events = list(events)[-self.MAX_EVENTS:]
            highest = max([e["id"] for e in self._events] or [0])
            self._last_id = max(self._last_id, highest)
            self._cond.notify_all()


_bus = EventBus()


def get_bus():
    return _bus
