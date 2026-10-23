import json
import unittest

import support
from AIAssistant.mcp import protocol
from AIAssistant.mcp.registry import ToolRegistry, ToolError
from AIAssistant.server.events import EventBus


def make_registry():
    registry = ToolRegistry()

    @registry.tool("add", "Add numbers", {"a": {"type": "number"}, "b": {"type": "number"}}, ["a", "b"])
    def add(args):
        return {"sum": args["a"] + args["b"]}

    @registry.tool("fail", "Always fails")
    def fail(args):
        raise ToolError("bad value")

    @registry.tool("crash", "Raises unexpected error")
    def crash(args):
        raise RuntimeError("boom")

    return registry


class ProtocolTest(unittest.TestCase):
    def setUp(self):
        self.registry = make_registry()
        self.bus = EventBus()

    def rpc(self, method, params=None, req_id=1):
        request = {"jsonrpc": "2.0", "id": req_id, "method": method}
        if params is not None:
            request["params"] = params
        return protocol.handle_request(request, self.registry, self.bus)

    def test_initialize_echoes_supported_version(self):
        response = self.rpc("initialize", {"protocolVersion": "2025-03-26"})
        self.assertEqual(response["result"]["protocolVersion"], "2025-03-26")
        self.assertEqual(response["result"]["serverInfo"]["name"], "ste-slicer-ai-assistant")

    def test_initialize_unknown_version_falls_back(self):
        response = self.rpc("initialize", {"protocolVersion": "1999-01-01"})
        self.assertEqual(response["result"]["protocolVersion"], "2025-06-18")

    def test_notification_has_no_response(self):
        request = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        self.assertIsNone(protocol.handle_request(request, self.registry, self.bus))

    def test_ping(self):
        self.assertEqual(self.rpc("ping")["result"], {})

    def test_tools_list(self):
        tools = self.rpc("tools/list")["result"]["tools"]
        self.assertEqual([t["name"] for t in tools], ["add", "fail", "crash"])
        self.assertIn("inputSchema", tools[0])

    def test_call_ok_publishes_events(self):
        response = self.rpc("tools/call", {"name": "add", "arguments": {"a": 1, "b": 2}})
        result = response["result"]
        self.assertFalse(result["isError"])
        self.assertEqual(json.loads(result["content"][0]["text"]), {"sum": 3})
        types_ = [e["type"] for e in self.bus.get_since(0)["events"]]
        self.assertEqual(types_, ["tool_call", "tool_result"])

    def test_call_missing_argument_is_tool_error(self):
        result = self.rpc("tools/call", {"name": "add", "arguments": {"a": 1}})["result"]
        self.assertTrue(result["isError"])
        self.assertIn("b", result["content"][0]["text"])

    def test_call_wrong_type_is_tool_error(self):
        result = self.rpc("tools/call", {"name": "add", "arguments": {"a": "x", "b": 2}})["result"]
        self.assertTrue(result["isError"])

    def test_tool_error_and_crash(self):
        self.assertTrue(self.rpc("tools/call", {"name": "fail"})["result"]["isError"])
        crash = self.rpc("tools/call", {"name": "crash"})["result"]
        self.assertTrue(crash["isError"])
        self.assertIn("boom", crash["content"][0]["text"])

    def test_unknown_tool_is_invalid_params(self):
        response = self.rpc("tools/call", {"name": "nope"})
        self.assertEqual(response["error"]["code"], protocol.INVALID_PARAMS)

    def test_unknown_method(self):
        self.assertEqual(self.rpc("foo")["error"]["code"], protocol.METHOD_NOT_FOUND)

    def test_parse_error(self):
        response = protocol.handle_body(b"{not json", self.registry, self.bus)
        self.assertEqual(response["error"]["code"], protocol.PARSE_ERROR)

    def test_invalid_request(self):
        response = protocol.handle_body(b'{"id": 3}', self.registry, self.bus)
        self.assertEqual(response["error"]["code"], protocol.INVALID_REQUEST)

    def test_utf8_body(self):
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}).encode("utf-8")
        self.assertEqual(protocol.handle_body(body, self.registry, self.bus)["result"], {})

    def test_openai_schema(self):
        tools = self.registry.list_openai()
        self.assertEqual(tools[0]["type"], "function")
        self.assertEqual(tools[0]["function"]["name"], "add")


class EventBusTest(unittest.TestCase):
    def test_limit_and_since(self):
        bus = EventBus()
        for i in range(1100):
            bus.publish("x", {"i": i})
        result = bus.get_since(0)
        self.assertEqual(len(result["events"]), 1000)
        self.assertEqual(result["last"], 1100)
        self.assertEqual(bus.get_since(1099)["events"][0]["id"], 1100)


if __name__ == "__main__":
    unittest.main()
