import json
import tempfile
import unittest
import urllib.error
import urllib.request

import support
from AIAssistant import config
from AIAssistant.agent.agent import get_agent
from AIAssistant.mcp.registry import get_registry
from AIAssistant.server.http_server import AssistantServer


class HttpTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        config.set_value("results_dir", cls.tmp)
        config.set_value("port", 0)
        get_registry().register("echo", "Echo", {"type": "object", "properties": {"text": {"type": "string"}}},
                                lambda args: {"echo": args.get("text")})
        cls.server = AssistantServer()
        cls.port = cls.server.start()
        cls.base = "http://127.0.0.1:%d" % cls.port

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def post(self, path, payload, headers=None):
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(self.base + path, data=data, method="POST")
        request.add_header("Content-Type", "application/json")
        for key, value in (headers or {}).items():
            request.add_header(key, value)
        return urllib.request.urlopen(request, timeout=10)

    def test_mcp_roundtrip(self):
        body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "echo", "arguments": {"text": "привет"}}}
        response = json.loads(self.post("/mcp", body).read().decode("utf-8"))
        self.assertEqual(json.loads(response["result"]["content"][0]["text"]), {"echo": "привет"})

    def test_mcp_notification_returns_202(self):
        response = self.post("/mcp", {"jsonrpc": "2.0", "method": "notifications/initialized"})
        self.assertEqual(response.status, 202)

    def test_events_contain_tool_calls(self):
        self.post("/mcp", {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "echo", "arguments": {}}})
        events = json.loads(urllib.request.urlopen(self.base + "/api/events?since=0").read().decode("utf-8"))
        names = [e["type"] for e in events["events"]]
        self.assertIn("tool_call", names)
        self.assertIn("tool_result", names)

    def test_foreign_origin_rejected(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.post("/mcp", {"jsonrpc": "2.0", "id": 1, "method": "ping"}, {"Origin": "http://evil.example"})
        self.assertEqual(ctx.exception.code, 403)

    def test_settings_mask_key(self):
        self.post("/api/settings", {"api_key": "sk-secret-value-1234", "model": "m1"})
        data = json.loads(urllib.request.urlopen(self.base + "/api/settings").read().decode("utf-8"))
        self.assertNotIn("secret", data["api_key"])
        self.assertTrue(data["api_key_set"])
        self.assertEqual(data["model"], "m1")

    def test_upload_rejects_bad_extension(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.post("/api/upload", {"name": "evil.exe", "data_base64": "AAAA"})
        self.assertEqual(ctx.exception.code, 400)

    def test_upload_model(self):
        import base64
        payload = {"name": "part.stl", "data_base64": base64.b64encode(b"solid x").decode("ascii")}
        data = json.loads(self.post("/api/upload", payload).read().decode("utf-8"))
        self.assertEqual(data["kind"], "model")
        with open(data["path"], "rb") as handle:
            self.assertEqual(handle.read(), b"solid x")

    def test_static_traversal_blocked(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(self.base + "/..%2f..%2fconfig.py")
        self.assertEqual(ctx.exception.code, 404)

    def test_message_without_llm_settings_reports_error(self):
        config.set_value("api_key", "")
        config.set_value("base_url", "")
        self.post("/api/message", {"text": "тест"})
        import time
        deadline = time.time() + 5
        found = False
        while time.time() < deadline and not found:
            events = json.loads(urllib.request.urlopen(self.base + "/api/events?since=0").read().decode("utf-8"))
            found = any(e["type"] == "error" for e in events["events"])
            time.sleep(0.1)
        self.assertTrue(found)


    def test_export_rejects_unknown_kind(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.post("/api/export", {"kind": "pdf"})
        self.assertEqual(ctx.exception.code, 400)

    def test_export_reports_tool_failure(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.post("/api/export", {"kind": "gcode"})
        self.assertEqual(ctx.exception.code, 409)

    def test_message_rejects_inline_attachment_with_bad_extension(self):
        import time
        deadline = time.time() + 5
        while get_agent().is_running() and time.time() < deadline:
            time.sleep(0.1)
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.post("/api/message", {"text": "x", "attachments": [{"name": "a.exe", "mime": "x", "data": "AAAA"}]})
        self.assertEqual(ctx.exception.code, 400)

    def test_settings_expose_ui_fields(self):
        data = json.loads(urllib.request.urlopen(self.base + "/api/settings").read().decode("utf-8"))
        self.assertIn("has_key", data)
        self.assertIn("explain", data)


if __name__ == "__main__":
    unittest.main()
