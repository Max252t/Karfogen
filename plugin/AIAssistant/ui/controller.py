import os
import threading
import time
import traceback

from PyQt5.QtCore import (QAbstractListModel, QModelIndex, QObject, Qt, QTimer, QUrl, pyqtProperty, pyqtSignal,
                          pyqtSlot)

from .. import config
from ..agent import llm_client
from ..agent.agent import get_agent
from ..mcp import protocol
from ..mcp.registry import get_registry
from ..server import projects, uploads
from ..server.events import get_bus
from . import live_status, strings, view_state

POLL_MS = 150
SCENE_REFRESH_S = 0.5
SLICER_REFRESH_S = 3.0
MESSAGE_ROLES = ("uid", "kind", "text", "title", "summary", "status", "details", "meta", "actions", "icon", "impact",
                 "phase", "progress", "percent", "indeterminate", "stageKey", "stages", "metrics", "changes",
                 "decisions", "exports", "blocks", "collapsible", "plain", "stageCount", "serious")
CHANGE_ROLES = ("key", "label", "old", "value")
DECISION_ROLES = ("label", "value", "reason")
PROJECT_ROLES = ("id", "name", "updated", "messages", "current")
ATTACHMENT_ROLES = ("id", "name", "kind", "size", "url", "path")
SCENE_ROLES = ("id", "name", "dims", "selected")
CONNECTION_ERRORS = ("not_configured", "auth", "not_found", "network", "timeout", "server", "ssl")


def _log(level, text):
    try:
        from UM.Logger import Logger
        Logger.log(level, "AIAssistant: " + text)
    except Exception:
        pass


class DictListModel(QAbstractListModel):
    countChanged = pyqtSignal()

    def __init__(self, roles, parent=None):
        super(DictListModel, self).__init__(parent)
        self._roles = list(roles)
        self._items = []

    def roleNames(self):
        return dict((Qt.UserRole + 1 + i, name.encode("utf-8")) for i, name in enumerate(self._roles))

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self._items)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._items):
            return None
        position = role - Qt.UserRole - 1
        if not 0 <= position < len(self._roles):
            return None
        return self._items[index.row()].get(self._roles[position], "")

    def items(self):
        return [dict(item) for item in self._items]

    def item(self, row):
        return dict(self._items[row])

    def setItems(self, items):
        self.beginResetModel()
        self._items = [dict(item) for item in items]
        self.endResetModel()
        self.countChanged.emit()

    def append(self, item):
        row = len(self._items)
        self.beginInsertRows(QModelIndex(), row, row)
        self._items.append(dict(item))
        self.endInsertRows()
        self.countChanged.emit()

    def update(self, row, item):
        if not 0 <= row < len(self._items):
            return
        old = self._items[row]
        roles = [Qt.UserRole + 1 + i for i, name in enumerate(self._roles) if old.get(name) != item.get(name)]
        self._items[row] = dict(item)
        if roles:
            index = self.index(row, 0)
            self.dataChanged.emit(index, index, roles)

    def remove(self, row):
        if not 0 <= row < len(self._items):
            return
        self.beginRemoveRows(QModelIndex(), row, row)
        del self._items[row]
        self.endRemoveRows()
        self.countChanged.emit()

    @pyqtProperty(int, notify=countChanged)
    def count(self):
        return len(self._items)


def url_to_path(value):
    if hasattr(value, "toVariant"):
        value = value.toVariant()
    if isinstance(value, QUrl):
        return value.toLocalFile()
    text = value.toString() if hasattr(value, "toString") and not isinstance(value, str) else str(value or "")
    if text.startswith("file:"):
        return QUrl(text).toLocalFile()
    return text


def current_language():
    return config.effective_language()


class NativeChatController(QObject):
    stateChanged = pyqtSignal()
    liveStatusChanged = pyqtSignal()
    languageChanged = pyqtSignal()
    settingsChanged = pyqtSignal()
    projectsChanged = pyqtSignal()
    sceneChanged = pyqtSignal()
    connectionChanged = pyqtSignal()
    testFinished = pyqtSignal(bool, str, arguments=["ok", "message"])
    toast = pyqtSignal(str, arguments=["message"])
    notify = pyqtSignal(str, str, arguments=["kind", "message"])
    showTab = pyqtSignal(str, arguments=["name"])
    openSettingsRequested = pyqtSignal()
    pickFileRequested = pyqtSignal()
    composerReset = pyqtSignal()
    _dispatch = pyqtSignal(object)

    def __init__(self, parent=None, agent=None, bus=None, registry=None, manager=None, start_timer=True):
        super(NativeChatController, self).__init__(parent)
        self._agent = agent or get_agent()
        self._bus = bus or get_bus()
        self._registry = registry or get_registry()
        self._manager = manager or projects.get_manager()
        if self._manager.agent is None:
            self._manager.attach(self._agent, self._bus)
        self._language = current_language()
        self._state = view_state.ChatViewState(self._language)
        self._live = live_status.LiveStatus(self._language)
        self._revision = None
        self._last_id = 0
        self._running = False
        self._mode = "auto"
        self._use_scene = False
        self._scene_selection = set()
        self._scene_objects = []
        self._scene_dirty = True
        self._scene_checked = 0.0
        self._slicer_checked = 0.0
        self._slicer_setup = {"mode": "", "material": "", "quality": "", "user_changes": 0, "slice": None}
        self._last_request = None
        self._connection = "unchecked"
        self._connection_detail = ""
        self._testing = False
        self._busy_action = ""
        self._window = None
        self._project_meta = None
        self.messages = DictListModel(MESSAGE_ROLES, self)
        self.changes = DictListModel(CHANGE_ROLES, self)
        self.decisions = DictListModel(DECISION_ROLES, self)
        self.projectList = DictListModel(PROJECT_ROLES, self)
        self.attachments = DictListModel(ATTACHMENT_ROLES, self)
        self.sceneObjects = DictListModel(SCENE_ROLES, self)
        self._dispatch.connect(self._run_dispatched, Qt.QueuedConnection)
        self._timer = QTimer(self)
        self._timer.setInterval(POLL_MS)
        self._timer.timeout.connect(self.tick)
        self.refreshProjects()
        self.tick()
        if start_timer:
            self._timer.start()

    def _run_dispatched(self, func):
        try:
            func()
        except Exception:
            _log("e", traceback.format_exc())

    def _later(self, func):
        self._dispatch.emit(func)

    def _background(self, name, work, done):
        def runner():
            try:
                result = (True, work())
            except Exception as e:
                _log("w", "%s failed: %s" % (name, e))
                result = (False, e)
            self._later(lambda: done(result[0], result[1]))
        thread = threading.Thread(target=runner, name="AIAssistant" + name)
        thread.daemon = True
        thread.start()
        return thread

    def t(self, key, *args):
        return strings.text(self._language, key, *args)

    def _notify(self, kind, message):
        self.toast.emit(message)
        self.notify.emit(kind, message)

    def setWindow(self, window):
        self._window = window

    def stop(self):
        self._timer.stop()

    @pyqtSlot()
    def tick(self):
        revision, reset, events = self._bus.read(self._revision, self._last_id)
        if reset:
            self._revision = revision
            self._state.rebuild(events)
            if not self._agent.is_running():
                self._state.finish_open_turn()
                self._state.ops = [("reset",)]
        else:
            for event in events:
                self._state.apply(event)
        if events:
            self._last_id = max(e["id"] for e in events)
        elif reset:
            self._last_id = 0
        changed = self._apply_ops(self._state.take_ops())
        if events and self._sync_side_models():
            changed = True
        running = bool(self._agent.is_running())
        if running != self._running:
            self._running = running
            changed = True
            if not running:
                self._state.finish_open_turn()
                self._apply_ops(self._state.take_ops())
                self._after_turn()
        if events:
            self._track_connection(events)
            if any(e["type"] == "status" and (e.get("data") or {}).get("text") == "slice_state" for e in events):
                self._slicer_checked = 0.0
        now = time.time()
        if self._scene_dirty and now - self._scene_checked >= SCENE_REFRESH_S:
            self._scene_dirty = False
            self._scene_checked = now
            self.refreshScene()
        if now - self._slicer_checked >= SLICER_REFRESH_S:
            self._slicer_checked = now
            if self._refresh_slicer():
                changed = True
        self._update_live_status(now)
        if changed or events:
            self.stateChanged.emit()

    def _update_live_status(self, now):
        stage, serious, active = self._state.live_stage()
        state = "running" if self._running and active else "idle"
        if self._live.update(stage, state, now, bool(config.get("live_status")), serious):
            self.liveStatusChanged.emit()

    @pyqtProperty(str, notify=liveStatusChanged)
    def liveStatus(self):
        return self._live.text

    def _apply_ops(self, ops):
        if not ops:
            return False
        for op in ops:
            if op[0] == "reset":
                self.messages.setItems(self._state.items)
            elif op[0] == "append":
                self.messages.append(self._state.items[op[1]])
            elif op[0] == "update":
                self.messages.update(op[1], self._state.items[op[1]])
        self._sync_side_models()
        return True

    def _sync_side_models(self):
        changed = False
        changes = self._state.changes_list()
        if changes != self.changes.items():
            self.changes.setItems(changes)
            changed = True
        if self._state.decisions != self.decisions.items():
            self.decisions.setItems(self._state.decisions)
            changed = True
        return changed

    def _track_connection(self, events):
        previous = self._connection
        for event in events:
            if event["type"] == "assistant_message" and not (event.get("data") or {}).get("code"):
                self._connection = "ok"
            elif event["type"] == "error":
                code = view_state.classify_error(event.get("data") or {})
                if code in CONNECTION_ERRORS:
                    self._connection = "error"
                    self._connection_detail = str((event.get("data") or {}).get("message") or "")
        if previous != self._connection:
            self.connectionChanged.emit()

    def _after_turn(self):
        self.refreshProjects()
        self._scene_dirty = True
        self._slicer_checked = 0.0

    def markSceneDirty(self, *args):
        self._scene_dirty = True

    @pyqtProperty("QVariantMap", notify=languageChanged)
    def strings(self):
        return dict(strings.table(self._language))

    @pyqtProperty(str, notify=languageChanged)
    def language(self):
        return self._language

    def _check_language(self):
        language = current_language()
        if language == self._language:
            return
        self._language = language
        self._state.language = language
        self._live.language = language
        self._live.reset()
        self._revision = None
        self._last_id = 0
        self.languageChanged.emit()
        self.tick()
        self.refreshProjects()

    @pyqtProperty(QObject, constant=True)
    def messageModel(self):
        return self.messages

    @pyqtProperty(QObject, constant=True)
    def changeModel(self):
        return self.changes

    @pyqtProperty(QObject, constant=True)
    def decisionModel(self):
        return self.decisions

    @pyqtProperty(QObject, constant=True)
    def projectModel(self):
        return self.projectList

    @pyqtProperty(QObject, constant=True)
    def attachmentModel(self):
        return self.attachments

    @pyqtProperty(QObject, constant=True)
    def sceneModel(self):
        return self.sceneObjects

    @pyqtProperty(bool, notify=stateChanged)
    def running(self):
        return self._running

    @pyqtProperty(bool, notify=stateChanged)
    def busy(self):
        return self._running or self._agent.is_running() or bool(self._busy_action)

    @pyqtProperty(bool, notify=stateChanged)
    def stopping(self):
        return self._running and self._state.status == "stopping"

    @pyqtProperty(str, notify=stateChanged)
    def statusText(self):
        return self._state.status_text() if self._running else ""

    @pyqtProperty(str, notify=stateChanged)
    def taskState(self):
        if self._running:
            return "running"
        return self._state.task_state

    @pyqtProperty(int, notify=stateChanged)
    def toolCount(self):
        return self._state.tool_count

    @pyqtProperty("QVariantList", notify=stateChanged)
    def changeList(self):
        return self.changes.items()

    @pyqtProperty("QVariantList", notify=stateChanged)
    def decisionList(self):
        return self.decisions.items()

    @pyqtProperty("QVariantList", notify=stateChanged)
    def stageHistory(self):
        return self._state.stage_history()

    @pyqtSlot(int, str, result=str)
    def countText(self, number, name):
        try:
            return strings.count(self._language, number, name)
        except KeyError:
            return str(number)

    @pyqtProperty(float, notify=stateChanged)
    def workProgress(self):
        turn = self._state.turn
        return float(turn.progress.value) if turn is not None else 0.0

    @pyqtSlot(str)
    def copyText(self, text):
        from PyQt5.QtGui import QGuiApplication
        QGuiApplication.clipboard().setText(text or "")
        self._notify("success", self.t("copied"))

    def slice_view(self):
        own = dict(self._state.slice)
        live = self._slicer_setup.get("slice")
        if live is None or (own["state"] == "slicing" and self._running):
            own.update({"live": live is not None, "ready": own["state"] == "done", "historical": False})
            return own
        view = dict(live)
        view["live"] = True
        view["ready"] = live["state"] == "done"
        view["historical"] = own["state"] == "done" and not view["ready"]
        if view["historical"]:
            view.update({"time": own["time"], "length": own["length"], "weight": own["weight"]})
        return view

    @pyqtProperty(str, notify=stateChanged)
    def sliceState(self):
        return self.slice_view()["state"]

    @pyqtProperty(float, notify=stateChanged)
    def sliceProgress(self):
        return float(self.slice_view()["progress"])

    @pyqtProperty("QVariantMap", notify=stateChanged)
    def sliceInfo(self):
        return self.slice_view()

    @pyqtProperty(str, notify=stateChanged)
    def appliedMode(self):
        return self._state.setup.get("mode") or ""

    @pyqtProperty("QVariantMap", notify=stateChanged)
    def setup(self):
        live = self._slicer_setup
        own = self._state.setup
        return {"mode": own.get("mode") or live.get("mode") or "",
                "material": own.get("material") or live.get("material") or "",
                "quality": own.get("quality") or live.get("quality") or "",
                "userChanges": int(live.get("user_changes") or 0)}

    @pyqtProperty("QVariantMap", notify=stateChanged)
    def exports(self):
        result = {"gcode": self._state.exports.get("gcode", ""), "3mf": self._state.exports.get("3mf", "")}
        result["busy"] = self._busy_action
        return result

    @pyqtProperty(str, notify=stateChanged)
    def mode(self):
        return self._mode

    @pyqtSlot(str)
    def setMode(self, mode):
        mode = mode if mode in view_state.FORCED_MODES else "auto"
        if mode != self._mode:
            self._mode = mode
            self.stateChanged.emit()

    def forced_mode(self):
        return view_state.normalize_mode(self._mode)

    @pyqtProperty(bool, notify=connectionChanged)
    def configured(self):
        return llm_client.is_configured()

    @pyqtProperty(str, notify=connectionChanged)
    def connectionState(self):
        if not llm_client.is_configured():
            return "not_configured"
        if self._testing:
            return "checking"
        return self._connection

    @pyqtProperty(str, notify=connectionChanged)
    def connectionText(self):
        state = self.connectionState
        text = self.t("conn_" + state)
        model = config.get("model")
        if state in ("ok", "unchecked") and model:
            return "%s · %s" % (text, model.split("/")[-1])
        return text

    @pyqtProperty(str, notify=connectionChanged)
    def connectionDetail(self):
        return self._connection_detail

    @pyqtProperty("QVariantMap", notify=settingsChanged)
    def settings(self):
        data = config.public_settings()
        data["api_key_mask"] = data.pop("api_key", "")
        slicer = config.normalize_language(data.get("slicer_language"))
        data["slicer_language_name"] = self.t("lang_" + slicer) if slicer else "%s → %s" % (
            data.get("slicer_language") or "—", self.t("lang_" + config.FALLBACK_LANGUAGE))
        effective = config.normalize_language(data.get("language_effective")) or config.FALLBACK_LANGUAGE
        data["language_effective_name"] = self.t("lang_" + effective)
        return data

    @pyqtSlot("QVariantMap", result=bool)
    def saveSettings(self, data):
        if self.busy:
            self._notify("warning", self.t("busy_send"))
            return False
        data = dict(data or {})
        clean = {}
        for key in ("base_url", "model", "results_dir"):
            if key in data:
                clean[key] = str(data[key] or "").strip()
        if str(data.get("language") or "") in config.LANGUAGE_MODES:
            clean["language"] = str(data["language"])
        for key in ("explain", "auto_export", "verify_ssl", "live_status"):
            if key in data:
                clean[key] = bool(data[key])
        key = str(data.get("api_key") or "").strip()
        if key:
            clean["api_key"] = key
        if clean.get("results_dir"):
            clean["results_dir"] = url_to_path(clean["results_dir"])
        folder_changed = "results_dir" in clean and clean["results_dir"] != config.get_results_dir()
        if folder_changed:
            self._manager.save_current()
        config.update_settings(clean)
        if folder_changed:
            self._manager.current_id = None
            self._agent.set_history([])
            self._bus.load([])
            self._last_request = None
            self._clear_composer()
            self.refreshProjects()
            self.tick()
        self._connection = "unchecked"
        self._connection_detail = ""
        self.settingsChanged.emit()
        self.connectionChanged.emit()
        self._check_language()
        self._notify("success", self.t("set_saved"))
        return True

    @pyqtSlot("QVariantMap")
    def testConnection(self, data):
        if self._testing:
            return
        data = dict(data or {})
        overrides = {}
        for key in ("base_url", "model", "api_key"):
            value = str(data.get(key) or "").strip()
            if value:
                overrides[key] = value
        base = overrides.get("base_url") or config.get("base_url")
        model = overrides.get("model") or config.get("model")
        key = overrides.get("api_key") or config.get("api_key")
        if not (base and model and key):
            self.testFinished.emit(False, self.t("set_test_need"))
            return
        self._testing = True
        self.connectionChanged.emit()
        tested = {"base_url": base, "model": model, "api_key": key}

        def done(ok, value):
            self._testing = False
            matches_saved = all(config.get(name) == value for name, value in tested.items())
            if ok:
                self._connection = "ok" if matches_saved else "unchecked"
                self._connection_detail = ""
                self.testFinished.emit(True, self.t("set_test_ok", value or "ok"))
            else:
                self._connection = "error" if matches_saved else "unchecked"
                self._connection_detail = str(value) if matches_saved else ""
                self.testFinished.emit(False, self.t("set_test_fail", self._explain_llm_error(value)))
            self.connectionChanged.emit()
        self._background("Test", lambda: llm_client.test_connection(overrides), done)

    def _explain_llm_error(self, error):
        code = view_state.classify_error({"code": getattr(error, "code", None), "message": str(error)})
        return "%s. %s" % (self.t("err_title_" + code), self.t("err_text_" + code))

    @pyqtSlot(result=bool)
    def checkConnection(self):
        if not llm_client.is_configured():
            return False
        self.testConnection({})
        return True

    @pyqtProperty(str, notify=projectsChanged)
    def projectName(self):
        return self._project_name(self._project_meta)

    @pyqtProperty(str, notify=projectsChanged)
    def projectId(self):
        meta = self._project_meta
        return meta["id"] if meta else ""

    @pyqtProperty(int, notify=projectsChanged)
    def projectMessages(self):
        meta = self._project_meta
        return int(meta.get("messages", 0)) if meta else 0

    @pyqtProperty(bool, notify=projectsChanged)
    def hasProjects(self):
        return self.projectList.count > 0

    def _project_name(self, meta):
        if not meta or meta.get("default_name"):
            return self.t("no_project")
        return meta["name"]

    def _format_date(self, ts):
        fmt = "%d.%m.%Y %H:%M" if self._language == "ru" else "%Y-%m-%d %H:%M"
        try:
            return time.strftime(fmt, time.localtime(float(ts)))
        except (TypeError, ValueError, OverflowError):
            return ""

    @pyqtSlot()
    def refreshProjects(self):
        try:
            items = projects.list_projects()
            self._project_meta = self._manager.current()
        except Exception as e:
            _log("e", "could not list projects: %s" % e)
            items = []
        current = self._project_meta["id"] if self._project_meta else None
        self.projectList.setItems([{"id": p["id"], "name": self._project_name(p), "updated": self._format_date(p["updated"]),
                                    "messages": int(p.get("messages", 0)), "current": p["id"] == current}
                                   for p in items])
        self.projectsChanged.emit()

    def _project_error(self, error):
        message = str(error)
        if isinstance(error, projects.ProjectError) and error.status == 409:
            message = self.t("proj_busy")
        self._notify("info", message)

    @pyqtSlot(bool, result=bool)
    def createProject(self, clear_scene):
        if self._busy_action:
            self._notify("warning", self.t("proj_busy"))
            return False
        try:
            self._manager.create(None, prepare=bool(clear_scene))
        except Exception as e:
            self._project_error(e)
            return False
        self._clear_composer()
        self._last_request = None
        self._mode = "auto"
        self.refreshProjects()
        self.tick()
        self.showTab.emit("chat")
        return True

    @pyqtSlot(str, result=bool)
    def openProject(self, project_id):
        if self._busy_action:
            self._notify("warning", self.t("proj_busy"))
            return False
        previous = self._manager.current_id
        try:
            meta = self._manager.open(project_id)
        except Exception as e:
            self._project_error(e)
            return False
        if previous != project_id:
            self._clear_composer()
            self._last_request = None
            self._mode = "auto"
        self.refreshProjects()
        self.tick()
        self.showTab.emit("chat")
        self._notify("info", self.t("proj_opened", meta["name"]))
        return True

    @pyqtSlot(str, str, result=bool)
    def renameProject(self, project_id, name):
        try:
            projects.rename_project(project_id, name)
        except Exception as e:
            self._project_error(e)
            return False
        self.refreshProjects()
        return True

    @pyqtSlot(str, result=bool)
    def deleteProject(self, project_id):
        if self._busy_action:
            self._notify("warning", self.t("proj_busy"))
            return False
        current = project_id == self._manager.current_id
        try:
            self._manager.delete(project_id)
        except Exception as e:
            self._project_error(e)
            return False
        if current:
            self._clear_composer()
            self._last_request = None
            self._mode = "auto"
        self.refreshProjects()
        self.tick()
        return True

    @pyqtSlot(QUrl, result=str)
    def urlToPath(self, url):
        return url_to_path(url)

    @pyqtSlot("QVariant", result=int)
    def addFiles(self, urls):
        if hasattr(urls, "toVariant"):
            urls = urls.toVariant()
        if isinstance(urls, (str, QUrl)):
            urls = [urls]
        added = []
        for value in urls or []:
            if self._add_file(url_to_path(value)):
                added.append(os.path.basename(url_to_path(value)))
        if len(added) == 1:
            self._notify("success", self.t("toast_file_added", added[0]))
        elif added:
            self._notify("success", self.t("attached_count", len(added)))
        return len(added)

    @pyqtSlot(str, result=bool)
    def addFile(self, url):
        return self.addFiles([url]) == 1

    def _file_problem(self, path):
        name = os.path.basename(path) or path
        ext = os.path.splitext(path)[1].lower()
        if ext not in uploads.IMAGE_EXTENSIONS + uploads.MODEL_EXTENSIONS:
            return self.t("file_bad_type", name)
        if not os.path.isfile(path):
            return self.t("file_missing", name)
        size = os.path.getsize(path)
        if size == 0:
            return self.t("file_empty", name)
        if size > uploads.MAX_BYTES:
            return self.t("file_too_big", name)
        if any(os.path.normcase(i["path"]) == os.path.normcase(os.path.abspath(path)) for i in self.attachments.items()):
            return self.t("file_duplicate", name)
        return None

    def _add_file(self, path):
        problem = self._file_problem(path) if path else self.t("file_missing", "")
        if problem:
            self._notify("warning", problem)
            return False
        try:
            item = uploads.register_file(path)
        except uploads.UploadError as e:
            self._notify("warning", str(e))
            return False
        self.attachments.append({"id": item["id"], "name": item["name"], "kind": item["kind"],
                                 "size": view_state.format_size(self._language, item["size"]),
                                 "url": QUrl.fromLocalFile(item["path"]).toString(), "path": item["path"]})
        self.stateChanged.emit()
        return True

    @pyqtSlot(str)
    def removeAttachment(self, item_id):
        for row, item in enumerate(self.attachments.items()):
            if item["id"] == item_id:
                self.attachments.remove(row)
                self.stateChanged.emit()
                return

    @pyqtSlot()
    def refreshScene(self):
        try:
            result = self._registry.call("list_objects", {}) if self._registry.has("list_objects") else {}
        except Exception as e:
            _log("w", "scene refresh failed: %s" % e)
            result = {}
        objects = []
        for obj in result.get("objects", []):
            if "size_mm" not in obj:
                continue
            objects.append({"id": obj["object_id"], "name": obj.get("name", ""),
                            "dims": "%s %s" % (view_state.format_dims(obj["size_mm"]), self.t("mm")),
                            "size": obj["size_mm"]})
        self.set_scene_objects(objects)

    def set_scene_objects(self, objects):
        ids = set(o["id"] for o in objects)
        self._scene_selection &= ids
        if not self._scene_selection and len(objects) == 1:
            self._scene_selection = set(ids)
        if not objects:
            self._use_scene = False
        self._scene_objects = list(objects)
        rows = [{"id": o["id"], "name": o["name"], "dims": o["dims"], "selected": o["id"] in self._scene_selection}
                for o in objects]
        if rows != self.sceneObjects.items():
            self.sceneObjects.setItems(rows)
        self.sceneChanged.emit()

    @pyqtProperty(bool, notify=sceneChanged)
    def useScene(self):
        return self._use_scene

    @pyqtSlot(bool)
    def setUseScene(self, value):
        self._use_scene = bool(value) and self.sceneObjects.count > 0
        if self._use_scene and not self._scene_selection:
            self._scene_selection = set(o["id"] for o in self.sceneObjects.items())
        self.set_scene_objects(self._scene_objects)

    @pyqtSlot(str)
    def toggleSceneObject(self, object_id):
        if object_id in self._scene_selection:
            self._scene_selection.discard(object_id)
        else:
            self._scene_selection.add(object_id)
        self.set_scene_objects(self._scene_objects)

    @pyqtSlot()
    def selectWholeScene(self):
        self._scene_selection = set(o["id"] for o in self.sceneObjects.items())
        self._use_scene = self.sceneObjects.count > 0
        self.set_scene_objects(self._scene_objects)

    @pyqtProperty(str, notify=sceneChanged)
    def sceneSubtitle(self):
        objects = self._scene_objects
        if len(objects) == 1:
            return "%s · %s" % (objects[0]["name"], objects[0]["dims"])
        if self._use_scene:
            return self.t("scene_selected", len(self.selected_scene_objects()), len(objects))
        return ", ".join(o["name"] for o in objects)

    @pyqtProperty(str, notify=stateChanged)
    def requestedMode(self):
        if self._last_request and self._last_request.get("mode"):
            return view_state.mode_label(self._last_request["mode"])
        return ""

    @pyqtProperty(str, notify=sceneChanged)
    def sceneSummary(self):
        selected = self.selected_scene_objects()
        if len(selected) == 1:
            return self.t("scene_using", "%s, %s" % (selected[0]["name"], selected[0]["dims"]))
        if selected:
            return self.t("scene_using_many", len(selected))
        return self.t("scene_use")

    def selected_scene_objects(self):
        return [o for o in self._scene_objects if o["id"] in self._scene_selection]

    def _refresh_slicer(self):
        try:
            from ..tools import settings_tools, slice_tools
            setup = settings_tools.current_setup()
            live = slice_tools.slice_snapshot()
            changed = self._registry.call("get_changed_settings", {}) if self._registry.has("get_changed_settings") \
                else {"changes": []}
        except Exception:
            return False
        materials = setup.get("materials") or {}
        material = materials.get("0") or materials.get(0) or (list(materials.values())[0] if materials else "")
        value = {"mode": view_state.mode_label(setup.get("print_mode")), "material": material or "",
                 "quality": setup.get("quality_type") or "", "user_changes": len(changed.get("changes") or []),
                 "slice": view_state.live_slice(self._language, live)}
        if value != self._slicer_setup:
            self._slicer_setup = value
            return True
        return False

    def _clear_composer(self):
        self.attachments.setItems([])
        self._use_scene = False
        self.composerReset.emit()
        self.sceneChanged.emit()

    @pyqtSlot(str, result=bool)
    def send(self, text):
        text = (text or "").strip()
        ids = [item["id"] for item in self.attachments.items()]
        scene = self.selected_scene_objects() if self._use_scene else []
        if not text and not ids and not scene:
            return False
        request = {"text": text, "ids": ids, "scene": scene, "mode": self.forced_mode(),
                   "files": self.attachments.items()}
        if not self._submit(request):
            return False
        self._clear_composer()
        return True

    def _submit(self, request):
        if self.busy:
            self._notify("warning", self.t("busy_send"))
            return False
        if not llm_client.is_configured():
            self.openSettingsRequested.emit()
            self.connectionChanged.emit()
            return False
        try:
            self._manager.ensure_current()
        except Exception as e:
            self._notify("info", str(e))
            return False
        notes = view_state.scene_note(request["scene"])
        display = {"scene": [o["name"] for o in request["scene"]]}
        ok, status = self._agent.submit(request["text"], request["ids"], None, request["mode"], notes, display)
        if not ok:
            self._notify("warning", self.t("busy_send"))
            return False
        self._last_request = request
        self._running = True
        try:
            self._manager.save_current()
        except Exception as e:
            _log("e", "could not save project: %s" % e)
        self.refreshProjects()
        self.tick()
        self.stateChanged.emit()
        return True

    @pyqtSlot(result=bool)
    def stopAgent(self):
        ok = self._agent.cancel()
        self.tick()
        return ok

    @pyqtSlot(str)
    def runAction(self, action):
        if action == "settings":
            self.openSettingsRequested.emit()
        elif action == "retry":
            self.retry()
        elif action == "continue":
            self.continueTask()
        elif action == "no_image":
            self.continueWithoutImage()
        elif action == "pick_file":
            self.pickFileRequested.emit()
        elif action in ("reset", "result"):
            self.showTab.emit("result")

    @pyqtSlot(result=bool)
    def retry(self):
        if self._last_request is None:
            return False
        return self._submit(self._last_request)

    @pyqtSlot(result=bool)
    def continueTask(self):
        mode = self._last_request["mode"] if self._last_request else self.forced_mode()
        return self._submit({"text": self.t("continue_prompt"), "ids": [], "scene": [], "mode": mode, "files": []})

    @pyqtSlot(result=bool)
    def continueWithoutImage(self):
        if self._last_request is None:
            return False
        request = dict(self._last_request)
        request["ids"] = [i for i in request["ids"] if (uploads.get_item(i) or {}).get("kind") != "image"]
        return self._submit(request)

    @pyqtProperty(bool, notify=stateChanged)
    def canRetry(self):
        return self._last_request is not None and not self.busy

    def _tool(self, name, args, title_key, success):
        if self.busy:
            self._notify("warning", self.t("busy_send"))
            return False
        self._busy_action = name
        self.stateChanged.emit()

        def work():
            result = protocol.call_tool(name, args, self._registry, self._bus)
            text = "".join(part.get("text", "") for part in result["content"])
            if result["isError"]:
                raise RuntimeError(text)
            return text

        def done(ok, value):
            self._busy_action = ""
            if ok:
                success(value)
            else:
                self._state.add_local_error(title_key, str(value))
                self._apply_ops(self._state.take_ops())
                self._notify("error", self.t(title_key))
            self._slicer_checked = 0.0
            self.tick()
            self._manager.save_current()
            self.stateChanged.emit()
        self._background("Tool", work, done)
        return True

    @pyqtSlot(str, result=bool)
    def exportFile(self, kind):
        name = {"gcode": "export_gcode", "3mf": "save_project_3mf"}.get(kind)
        if name is None:
            return False
        return self._tool(name, {}, "err_title_export",
                          lambda value: self._notify("success", self.t("toast_export", self._last_export_path(kind))))

    def _last_export_path(self, kind):
        self.tick()
        return self._state.exports.get(kind, "")

    @pyqtSlot(result=bool)
    def resetChanges(self):
        if self._running:
            self._notify("warning", self.t("busy_send"))
            return False
        return self._tool("reset_settings", {}, "err_title_internal", lambda value: self._notify("success", self.t("res_reset_done")))

    def _results_folder(self):
        for kind in ("gcode", "3mf"):
            path = self._state.exports.get(kind)
            if path and os.path.isdir(os.path.dirname(path)):
                return os.path.dirname(path)
        return config.get_results_dir()

    @pyqtSlot(result=bool)
    def openResultsFolder(self):
        from PyQt5.QtGui import QDesktopServices
        folder = self._results_folder()
        if not os.path.isdir(folder):
            os.makedirs(folder)
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(folder)):
            self._notify("error", self.t("toast_folder_fail"))
            return False
        return True

    @pyqtSlot()
    def windowShown(self):
        self._check_language()
        self.settingsChanged.emit()
        self.connectionChanged.emit()
        self.refreshProjects()
        self._scene_dirty = True
        self._slicer_checked = 0.0
        self.tick()

    @pyqtProperty(str, constant=True)
    def initialTab(self):
        if self._manager.current() is None and self.projectList.count > 0:
            return "projects"
        return "chat"
