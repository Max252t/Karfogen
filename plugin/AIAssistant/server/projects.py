import json
import os
import shutil
import threading
import time
import uuid

from .events import VOLATILE_TYPES

from .. import config
from ..cad.store import get_store
from . import titles

MAX_NAME = 80
MAX_RESULT_CHARS = 20000
AUTOSAVE_INTERVAL = 5
DEFAULT_NAMES = tuple(titles.DEFAULT_TITLES.values())


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


def compact_volatile(events):
    last = {}
    for index, event in enumerate(events):
        if event.get("type") in VOLATILE_TYPES:
            last[event["type"]] = index
    return [event for index, event in enumerate(events)
            if event.get("type") not in VOLATILE_TYPES or last.get(event["type"]) == index]


def _trim_events(events):
    result = []
    for event in compact_volatile(events):
        data = event.get("data") or {}
        res = data.get("result")
        if isinstance(res, str) and len(res) > MAX_RESULT_CHARS:
            event = dict(event)
            data = dict(data)
            data["result"] = res[:MAX_RESULT_CHARS] + "...[обрезано]"
            event["data"] = data
        result.append(event)
    return result


_write_lock = threading.RLock()


def _log(level, text):
    try:
        from UM.Logger import Logger
        Logger.log(level, "AIAssistant: " + text)
    except Exception:
        pass


def heal_events(events, history, service=()):
    has_user = any(event.get("type") == "user_message" for event in events)
    rebuilt = [event for event in events_from_history(history)
               if not (event["type"] == "user_message" and event["data"]["text"] in service)]
    if has_user or not any(event["type"] == "user_message" for event in rebuilt):
        return events
    present = set((event["type"], (event.get("data") or {}).get("text")) for event in events)
    prefix = [event for event in rebuilt if (event["type"], event["data"]["text"]) not in present]
    return prefix + list(events)


NOTE_PREFIXES = ("Режим печати зафиксирован", "Прикреплено изображение", "Прикреплён файл", "Имя результата",
                 "Язык ответа:", "Reply language:")


def strip_notes(content):
    blocks = content.split("\n\n")
    if len(blocks) > 1:
        lines = [line for line in blocks[-1].split("\n") if line]
        if lines and all(line.startswith(NOTE_PREFIXES) for line in lines):
            return "\n\n".join(blocks[:-1])
    return content


def events_from_history(history):
    events = []
    for index, message in enumerate(history):
        role = message.get("role")
        content = message.get("content")
        if isinstance(content, list):
            content = " ".join(p.get("text", "") for p in content if p.get("type") == "text")
        if role == "user" and content:
            text = strip_notes(content)
            events.append({"id": len(events) + 1, "ts": 0, "type": "user_message", "data": {"text": text}})
        elif role == "assistant" and content:
            events.append({"id": len(events) + 1, "ts": 0, "type": "assistant_message", "data": {"text": content}})
    return events


def _read(project_id):
    path = _file(project_id)
    with _write_lock:
        if not os.path.isfile(path):
            raise ProjectError("Проект не найден", 404)
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)


def _write(project):
    with _write_lock:
        folder = _dir(project["id"])
        if not os.path.isdir(folder):
            os.makedirs(folder)
        tmp = "%s.%s.tmp" % (_file(project["id"]), uuid.uuid4().hex[:8])
        try:
            with open(tmp, "w", encoding="utf-8") as handle:
                json.dump(project, handle, ensure_ascii=False, default=str)
            os.replace(tmp, _file(project["id"]))
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)


def title_source(project):
    source = project.get("title_source")
    if source in ("default", "auto", "manual"):
        return source
    if not project.get("auto_named"):
        return "manual"
    name = project.get("name") or ""
    return "default" if name in DEFAULT_NAMES or titles.is_contentless(name) else "auto"


def _meta(project):
    waiting = bool(project.get("auto_named")) and title_source(project) == "default"
    return {
        "id": project["id"],
        "name": project["name"],
        "created": project["created"],
        "updated": project["updated"],
        "messages": project.get("messages", 0),
        "auto_named": project.get("auto_named", False),
        "default_name": waiting,
        "wants_title": waiting,
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
        "name": _clean_name(name) if name else titles.DEFAULT_TITLES[config.effective_language()],
        "auto_named": not name,
        "title_source": "manual" if name else "default",
        "created": now,
        "updated": now,
        "messages": 0,
        "history": [],
        "events": [],
    }
    _write(project)
    return _meta(project)


def rename_project(project_id, name):
    clean = _clean_name(name)
    with _write_lock:
        project = _read(project_id)
        project["name"] = clean
        project["auto_named"] = False
        project["title_source"] = "manual"
        _write(project)
        return _meta(project)


def delete_project(project_id):
    with _write_lock:
        _read(project_id)
        shutil.rmtree(_dir(project_id))


def load_project(project_id):
    return _read(project_id)


def save_project(project_id, events, history, title=None, generated=None):
    trimmed_events = _trim_events(events)
    stripped_history = _strip_images(history)
    messages = len([m for m in history if m.get("role") == "user"])
    with _write_lock:
        project = _read(project_id)
        project["events"] = trimmed_events
        project["history"] = stripped_history
        project["messages"] = messages
        if generated is not None:
            project["generated_models"] = generated
        project["updated"] = time.time()
        clean = titles.sanitize_title(title) if title else None
        if clean and project.get("auto_named") and title_source(project) == "default":
            project["name"] = clean
            project["title_source"] = "auto"
        elif "title_source" not in project:
            project["title_source"] = title_source(project)
        _write(project)
        return _meta(project)


def service_prompts():
    from ..ui import strings
    return tuple(strings.text(language, "continue_prompt") for language in strings.TABLES)


def title_from_events(events):
    return titles.title_from_events(events, config.effective_language(), service_prompts())


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
        agent.title_handler = self
        self._pending_title = None

    def wants_title(self):
        meta = self.current()
        pending = getattr(self, "_pending_title", None)
        return bool(meta and meta["wants_title"] and (pending is None or pending[0] != self.current_id))

    def propose_title(self, title):
        clean = titles.sanitize_title(title)
        if not clean or not self.wants_title():
            return False
        self._pending_title = (self.current_id, clean)
        return True

    def _title_for(self, project_id, events):
        pending = getattr(self, "_pending_title", None)
        if pending and pending[0] == project_id:
            return pending[1]
        return title_from_events(events)

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
                self.current_id = create_project()["id"]
            return self.current_id

    def create(self, name=None, prepare=True):
        self._require_idle()
        with self._lock:
            self.save_current()
            if prepare:
                self.prepare_slicer()
            meta = create_project(name)
            self.current_id = meta["id"]
            get_store().clear()
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
            if history:
                events = heal_events(events, history, service_prompts())
            get_store().load(project.get("generated_models") or [])
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
                get_store().clear()
                self.agent.set_history([])
                self.bus.load([])

    def save_current(self):
        if self.current_id is None or self.agent is None:
            return
        history = self.agent.get_history()
        events = self.bus.snapshot()
        try:
            project_id = self.current_id
            meta = save_project(project_id, events, history, self._title_for(project_id, events),
                                get_store().snapshot())
            if not meta["wants_title"]:
                self._pending_title = None
            self._last_autosave = time.time()
        except Exception as e:
            _log("e", "could not save project %s: %s" % (self.current_id, e))

    def autosave(self):
        if time.time() - getattr(self, "_last_autosave", 0) >= AUTOSAVE_INTERVAL:
            self.save_current()


_manager = ProjectManager()


def get_manager():
    return _manager
