import json
import mimetypes
import os
import socketserver
import threading
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

from .. import config
from ..agent import knowledge, llm_client
from ..agent.agent import get_agent
from ..mcp import protocol
from ..mcp.registry import get_registry
from . import projects, uploads
from .events import get_bus

WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")
MAX_BODY = 150 * 1024 * 1024
LOOPBACK_HOSTS = ("127.0.0.1", "localhost")


def _log(level, text):
    try:
        from UM.Logger import Logger
        Logger.log(level, "AIAssistant: " + text)
    except Exception:
        pass


class _Server(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class ApiError(Exception):
    def __init__(self, message, status=400):
        super(ApiError, self).__init__(message)
        self.status = status


class Handler(BaseHTTPRequestHandler):
    server_version = "AIAssistant/1.0"

    def log_message(self, fmt, *args):
        pass

    def _host_ok(self):
        host = self.headers.get("Host", "")
        name = host.rsplit(":", 1)[0] if ":" in host else host
        if name not in LOOPBACK_HOSTS:
            return False
        origin = self.headers.get("Origin")
        if origin:
            parsed = urlparse(origin)
            if parsed.hostname not in LOOPBACK_HOSTS or parsed.port != self.server.server_address[1]:
                return False
        return True

    def _send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            raise ApiError("Тело запроса слишком большое", 413)
        return self.rfile.read(length) if length else b""

    def _read_json(self):
        raw = self._read_body()
        if not raw:
            return {}
        try:
            data = json.loads(raw.decode("utf-8"))
        except ValueError:
            raise ApiError("Некорректный JSON")
        if not isinstance(data, dict):
            raise ApiError("Ожидался JSON-объект")
        return data

    def do_GET(self):
        if not self._host_ok():
            self._send_json({"error": "forbidden"}, 403)
            return
        try:
            parsed = urlparse(self.path)
            if parsed.path.startswith("/api/"):
                self._api_get(parsed)
            else:
                self._static(parsed.path)
        except (ApiError, projects.ProjectError) as e:
            self._send_json({"error": str(e)}, e.status)
        except Exception as e:
            _log("e", traceback.format_exc())
            self._send_json({"error": "%s: %s" % (e.__class__.__name__, e)}, 500)

    def do_POST(self):
        if not self._host_ok():
            self._send_json({"error": "forbidden"}, 403)
            return
        try:
            path = urlparse(self.path).path
            if path == "/mcp":
                self._mcp()
            elif path.startswith("/api/"):
                self._api_post(path)
            else:
                raise ApiError("Не найдено", 404)
        except (ApiError, projects.ProjectError) as e:
            self._send_json({"error": str(e)}, e.status)
        except Exception as e:
            _log("e", traceback.format_exc())
            self._send_json({"error": "%s: %s" % (e.__class__.__name__, e)}, 500)

    def _mcp(self):
        body = self._read_body()
        response = protocol.handle_body(body, get_registry(), get_bus())
        if response is None:
            self.send_response(202)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self._send_json(response)

    def _static(self, path):
        if path in ("", "/"):
            path = "/index.html"
        relative = os.path.normpath(path.lstrip("/"))
        full = os.path.abspath(os.path.join(WEB_DIR, relative))
        if not full.startswith(os.path.abspath(WEB_DIR) + os.sep) or not os.path.isfile(full):
            raise ApiError("Не найдено", 404)
        with open(full, "rb") as handle:
            data = handle.read()
        ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
            ctype += "; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def _api_get(self, parsed):
        query = parse_qs(parsed.query)
        if parsed.path == "/api/events":
            since = int((query.get("since") or ["0"])[0])
            wait = min(float((query.get("wait") or ["0"])[0]), 25.0)
            self._send_json(get_bus().get_since(since, wait))
        elif parsed.path == "/api/settings":
            self._send_json(config.public_settings())
        elif parsed.path == "/api/projects":
            self._send_json(self._projects_state())
        elif parsed.path == "/api/state":
            self._send_json({"running": get_agent().is_running(), "tools": get_registry().names()})
        else:
            raise ApiError("Не найдено", 404)

    def _api_post(self, path):
        data = self._read_json()
        if path == "/api/message":
            text = (data.get("text") or "").strip()
            attachment_ids = self._resolve_attachments(data.get("attachments") or [])
            if not text and not attachment_ids:
                raise ApiError("Пустое сообщение")
            projects.get_manager().ensure_current()
            mode = data.get("mode")
            forced = mode if mode in knowledge.MODE_LABELS else None
            ok, status = get_agent().submit(text, attachment_ids, data.get("model_name"), forced)
            if not ok:
                self._send_json({"ok": False, "error": status}, 409)
                return
            projects.get_manager().save_current()
            self._send_json({"ok": True})
        elif path == "/api/upload":
            try:
                item = uploads.save_upload(data.get("name", ""), data.get("data_base64", ""))
            except uploads.UploadError as e:
                raise ApiError(str(e))
            self._send_json({"id": item["id"], "name": item["name"], "kind": item["kind"], "path": item["path"]})
        elif path == "/api/settings":
            self._send_json(config.update_settings(data))
        elif path == "/api/export":
            self._send_json(self._export(data))
        elif path == "/api/projects":
            self._send_json(self._projects_action(data))
        elif path == "/api/choose_folder":
            self._send_json(self._choose_folder(data))
        elif path == "/api/test_connection":
            try:
                answer = llm_client.test_connection()
            except llm_client.LLMError as e:
                self._send_json({"ok": False, "error": str(e)})
                return
            self._send_json({"ok": True, "answer": answer})
        elif path == "/api/cancel":
            self._send_json({"ok": get_agent().cancel()})
        elif path == "/api/reset":
            if not get_agent().reset():
                raise ApiError("Ассистент занят", 409)
            if data.get("reset_settings"):
                get_registry().call("reset_settings", {})
            self._send_json({"ok": True})
        else:
            raise ApiError("Не найдено", 404)

    def _projects_state(self):
        manager = projects.get_manager()
        return {"projects": projects.list_projects(), "current": manager.current()}

    def _projects_action(self, data):
        manager = projects.get_manager()
        action = data.get("action")
        if action == "create":
            manager.create(data.get("name"))
        elif action == "open":
            manager.open(data.get("id"))
        elif action == "rename":
            projects.rename_project(data.get("id"), data.get("name"))
        elif action == "delete":
            manager.delete(data.get("id"))
        else:
            raise ApiError("Неизвестное действие")
        return self._projects_state()

    def _choose_folder(self, data):
        from ..tools.main_thread import run_on_main

        def dialog():
            from PyQt5.QtWidgets import QFileDialog
            start = data.get("start") or config.get_results_dir()
            return QFileDialog.getExistingDirectory(None, "Папка результатов", start)

        path = run_on_main(dialog, _timeout=600)
        return {"path": path or None}

    def _resolve_attachments(self, items):
        ids = []
        for item in items:
            if isinstance(item, str):
                ids.append(item)
            elif isinstance(item, dict):
                try:
                    saved = uploads.save_upload(item.get("name", ""), item.get("data") or item.get("data_base64") or "")
                except uploads.UploadError as e:
                    raise ApiError(str(e))
                ids.append(saved["id"])
        return ids

    def _export(self, data):
        tools = {"gcode": "export_gcode", "3mf": "save_project_3mf"}
        name = tools.get(data.get("kind"))
        if name is None:
            raise ApiError("kind должен быть gcode или 3mf")
        args = {"model_name": data["model_name"]} if data.get("model_name") else {}
        result = protocol.call_tool(name, args, get_registry(), get_bus())
        text = "".join(part.get("text", "") for part in result["content"])
        if result["isError"]:
            raise ApiError(text, 409)
        return json.loads(text)


class AssistantServer(object):
    def __init__(self):
        self._httpd = None
        self._thread = None
        self.port = None

    def start(self):
        if self._httpd is not None:
            return self.port
        projects.get_manager().attach(get_agent(), get_bus())
        preferred = config.get("port")
        try:
            self._httpd = _Server(("127.0.0.1", preferred), Handler)
        except OSError:
            self._httpd = _Server(("127.0.0.1", 0), Handler)
        self.port = self._httpd.server_address[1]
        self._thread = threading.Thread(target=self._httpd.serve_forever, name="AIAssistantHTTP")
        self._thread.daemon = True
        self._thread.start()
        _log("i", "server listening on 127.0.0.1:%d" % self.port)
        return self.port

    def stop(self):
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
            self.port = None

    def url(self):
        return "http://127.0.0.1:%d/" % self.port if self.port else None
