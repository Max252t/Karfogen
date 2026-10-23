import json
import os
import re
import shutil
import threading
import time
import uuid

from .. import config

MAX_NAME = 80
MAX_RESULT_CHARS = 20000
AUTOSAVE_INTERVAL = 5
DEFAULT_NAMES = ("Новый проект", "New project")


class ProjectError(Exception):
    def __init__(self, message, status=400):
        super(ProjectError, self).__init__(message)
        self.status = status


def _root():
    path = os.path.join(config.get_results_dir(), "_projects")
    if not os.path.isdir(path):
        os.makedirs(path)
    return path


def _dir(project_id):
    if not project_id or not project_id.isalnum():
        raise ProjectError("Некорректный id проекта")
    return os.path.join(_root(), project_id)


def _file(project_id):
    return os.path.join(_dir(project_id), "project.json")


def _clean_name(name):
    name = " ".join(str(name or "").split())
    if not name:
        raise ProjectError("Имя проекта не может быть пустым")
    return name[:MAX_NAME]


def _strip_images(history):
    result = []
    for message in history:
        content = message.get("content")
        if isinstance(content, list):
            texts = [p.get("text", "") for p in content if p.get("type") == "text"]
            message = dict(message)
            message["content"] = "\n".join(texts) + "\n[изображения не сохранены]"
        result.append(message)
    return result


def _trim_events(events):
    result = []
    for event in events:
        data = event.get("data") or {}
        res = data.get("result")
        if isinstance(res, str) and len(res) > MAX_RESULT_CHARS:
            event = dict(event)
            data = dict(data)
            data["result"] = res[:MAX_RESULT_CHARS] + "...[обрезано]"
            event["data"] = data
        result.append(event)
    return result


def _log(level, text):
    try:
        from UM.Logger import Logger
        Logger.log(level, "AIAssistant: " + text)
    except Exception:
        pass


def events_from_history(history):
    events = []
    for index, message in enumerate(history):
        role = message.get("role")
        content = message.get("content")
        if isinstance(content, list):
            content = " ".join(p.get("text", "") for p in content if p.get("type") == "text")
        if role == "user" and content:
            text = content.split("\n\n")[0]
            events.append({"id": len(events) + 1, "ts": 0, "type": "user_message", "data": {"text": text}})
        elif role == "assistant" and content:
            events.append({"id": len(events) + 1, "ts": 0, "type": "assistant_message", "data": {"text": content}})
    return events


def _read(project_id):
    path = _file(project_id)
    if not os.path.isfile(path):
        raise ProjectError("Проект не найден", 404)
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _write(project):
    folder = _dir(project["id"])
    if not os.path.isdir(folder):
        os.makedirs(folder)
    tmp = _file(project["id"]) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(project, handle, ensure_ascii=False, default=str)
    os.replace(tmp, _file(project["id"]))


def _meta(project):
    return {
        "id": project["id"],
        "name": project["name"],
        "created": project["created"],
        "updated": project["updated"],
        "messages": project.get("messages", 0),
        "auto_named": project.get("auto_named", False),
    }


def list_projects():
    result = []
    root = _root()
    for name in os.listdir(root):
        path = os.path.join(root, name, "project.json")
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as handle:
                result.append(_meta(json.load(handle)))
        except (ValueError, KeyError, OSError):
            continue
    result.sort(key=lambda p: -p["updated"])
    return result


def create_project(name=None):
    now = time.time()
    project = {
        "id": uuid.uuid4().hex[:12],
        "name": _clean_name(name) if name else DEFAULT_NAMES[0],
        "auto_named": not name,
        "created": now,
        "updated": now,
        "messages": 0,
        "history": [],
        "events": [],
    }
    _write(project)
    return _meta(project)


def rename_project(project_id, name):
    project = _read(project_id)
    project["name"] = _clean_name(name)
    project["auto_named"] = False
    _write(project)
    return _meta(project)


def delete_project(project_id):
    _read(project_id)
    shutil.rmtree(_dir(project_id))


def load_project(project_id):
    return _read(project_id)


def save_project(project_id, events, history, auto_name=None):
    project = _read(project_id)
    project["events"] = _trim_events(events)
    project["history"] = _strip_images(history)
    project["messages"] = len([m for m in history if m.get("role") == "user"])
    project["updated"] = time.time()
    if auto_name and project.get("auto_named"):
        project["name"] = _clean_name(auto_name)
    _write(project)
    return _meta(project)


def name_from_history(history):
    for message in history:
        if message.get("role") != "user":
            continue
        content = message.get("content")
        if isinstance(content, list):
            content = " ".join(p.get("text", "") for p in content if p.get("type") == "text")
        content = content or ""
        found = re.search(r"Прикреплён файл: ([^\n]+?), путь:", content)
        text = content.split("\n\n")[0]
        return suggest_name(text, found.group(1) if found else None)
    return None


def suggest_name(text, model_file=None):
    if model_file:
        base = os.path.splitext(os.path.basename(model_file))[0].strip()
        if base:
            return base
    first = " ".join((text or "").split())
    return first[:40] if first else None


class ProjectManager(object):
    def __init__(self):
        self._lock = threading.Lock()
        self.current_id = None
        self.agent = None
        self.bus = None

    def attach(self, agent, bus):
        self.agent = agent
        self.bus = bus
        agent.on_finished = self.save_current
        agent.on_progress = self.autosave

    def current(self):
        if self.current_id is None:
            return None
        try:
            return _meta(_read(self.current_id))
        except ProjectError:
            self.current_id = None
            return None

    def _require_idle(self):
        if self.agent is not None and self.agent.is_running():
            raise ProjectError("Ассистент занят, дождитесь ответа", 409)

    def prepare_slicer(self):
        from ..mcp import protocol
        from ..mcp.registry import get_registry
        registry = get_registry()
        for name in ("clear_scene", "reset_settings"):
            if registry.has(name):
                try:
                    protocol.call_tool(name, {}, registry, None)
                except Exception:
                    pass

    def ensure_current(self):
        with self._lock:
            if self.current() is None:
                self.prepare_slicer()
                self.current_id = create_project()["id"]
            return self.current_id

    def create(self, name=None):
        self._require_idle()
        with self._lock:
            self.save_current()
            self.prepare_slicer()
            meta = create_project(name)
            self.current_id = meta["id"]
            self.agent.set_history([])
            self.bus.load([])
            return meta

    def open(self, project_id):
        if project_id == self.current_id and self.current() is not None:
            return self.current()
        self._require_idle()
        with self._lock:
            if project_id != self.current_id:
                self.save_current()
            project = load_project(project_id)
            self.current_id = project_id
            history = project.get("history", [])
            events = project.get("events", [])
            if not events and history:
                events = events_from_history(history)
            self.agent.set_history(history)
            self.bus.load(events)
            return _meta(project)

    def delete(self, project_id):
        if project_id == self.current_id:
            self._require_idle()
        with self._lock:
            delete_project(project_id)
            if self.current_id == project_id:
                self.current_id = None
                self.agent.set_history([])
                self.bus.load([])

    def save_current(self):
        if self.current_id is None or self.agent is None:
            return
        history = self.agent.get_history()
        try:
            save_project(self.current_id, self.bus.snapshot(), history, name_from_history(history))
            self._last_autosave = time.time()
        except Exception as e:
            _log("e", "could not save project %s: %s" % (self.current_id, e))

    def autosave(self):
        if time.time() - getattr(self, "_last_autosave", 0) >= AUTOSAVE_INTERVAL:
            self.save_current()


_manager = ProjectManager()


def get_manager():
    return _manager
