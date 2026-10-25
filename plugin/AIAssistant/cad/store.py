import copy
import threading
import uuid
from collections import OrderedDict

from . import schema

SCENE_SESSION_ID = uuid.uuid4().hex


class ModelStore(object):
    def __init__(self):
        self._lock = threading.RLock()
        self._models = OrderedDict()

    def put(self, spec):
        with self._lock:
            self._models[spec["model_id"]] = spec
        return spec

    def get(self, model_id):
        with self._lock:
            return self._models.get(model_id)

    def find(self, identifier=None):
        with self._lock:
            if identifier is None:
                if len(self._models) == 1:
                    return list(self._models.values())[0]
                return None
            if identifier in self._models:
                return self._models[identifier]
            for spec in self._models.values():
                if spec.get("object_id") == identifier:
                    return spec
            return None

    def all(self):
        with self._lock:
            return list(self._models.values())

    def clear(self):
        with self._lock:
            self._models.clear()

    def snapshot(self):
        with self._lock:
            return copy.deepcopy(list(self._models.values()))

    def load(self, specs):
        with self._lock:
            self._models.clear()
            for spec in specs or []:
                if self._acceptable(spec):
                    loaded = copy.deepcopy(spec)
                    if loaded.get("scene_session_id") != SCENE_SESSION_ID:
                        loaded["object_id"] = None
                    self._models[loaded["model_id"]] = loaded

    @staticmethod
    def _acceptable(spec):
        if not isinstance(spec, dict):
            return False
        if spec.get("part_type") not in schema.PARTS or not spec.get("model_id"):
            return False
        return isinstance(spec.get("requested"), dict) and isinstance(spec.get("parameters"), dict)


_store = ModelStore()


def get_store():
    return _store
