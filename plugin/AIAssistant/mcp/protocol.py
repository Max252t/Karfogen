import itertools
import json

from .registry import get_registry, run_guarded
from ..server.derived_events import publish_derived

SUPPORTED_VERSIONS = ["2025-06-18", "2025-03-26", "2024-11-05"]
SERVER_INFO = {"name": "ste-slicer-ai-assistant", "version": "1.0.0"}

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

_call_counter = itertools.count(1)


def _error(req_id, code, message):
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _result(req_id, result):
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _publish(bus, event_type, data):
    if bus is not None:
        bus.publish(event_type, data)


def call_tool(name, arguments, registry=None, bus=None):
    registry = registry or get_registry()
    call_id = "c%d" % next(_call_counter)
    _publish(bus, "tool_call", {"call_id": call_id, "name": name, "arguments": arguments})
    ok, payload, duration = run_guarded(registry, name, arguments)
    if ok:
        text = json.dumps(payload, ensure_ascii=False, default=str)
        _publish(bus, "tool_result", {"call_id": call_id, "name": name, "ok": True,
                                      "result": payload, "duration_ms": duration})
        if bus is not None:
            try:
                publish_derived(bus, registry, name, arguments, payload)
            except Exception:
                pass
        return {"content": [{"type": "text", "text": text}], "isError": False}
    _publish(bus, "tool_result", {"call_id": call_id, "name": name, "ok": False,
                                  "error": payload, "duration_ms": duration})
    return {"content": [{"type": "text", "text": str(payload)}], "isError": True}


def handle_request(request, registry=None, bus=None):
    registry = registry or get_registry()
    if not isinstance(request, dict) or request.get("jsonrpc") != "2.0" or "method" not in request:
        return _error(request.get("id") if isinstance(request, dict) else None,
                      INVALID_REQUEST, "Invalid Request")
    method = request["method"]
    params = request.get("params")
    if params is None:
        params = {}
    req_id = request.get("id")
    if not isinstance(method, str) or not isinstance(params, dict):
        return _error(req_id, INVALID_REQUEST, "Invalid Request")

    if "id" not in request:
        return None

    try:
        if method == "initialize":
            version = params.get("protocolVersion")
            if version not in SUPPORTED_VERSIONS:
                version = SUPPORTED_VERSIONS[0]
            return _result(req_id, {
                "protocolVersion": version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": SERVER_INFO,
            })
        if method == "ping":
            return _result(req_id, {})
        if method == "tools/list":
            return _result(req_id, {"tools": registry.list_mcp()})
        if method == "tools/call":
            name = params.get("name")
            if not isinstance(name, str) or not registry.has(name):
                return _error(req_id, INVALID_PARAMS, "Unknown tool: %s" % name)
            arguments = params.get("arguments")
            if arguments is None:
                arguments = {}
            if not isinstance(arguments, dict):
                return _error(req_id, INVALID_PARAMS, "arguments must be an object")
            return _result(req_id, call_tool(name, arguments, registry, bus))
        return _error(req_id, METHOD_NOT_FOUND, "Method not found: %s" % method)
    except Exception as e:
        return _error(req_id, INTERNAL_ERROR, "%s: %s" % (e.__class__.__name__, e))


def handle_body(body, registry=None, bus=None):
    try:
        if isinstance(body, bytes):
            body = body.decode("utf-8")
        request = json.loads(body)
    except Exception:
        return _error(None, PARSE_ERROR, "Parse error")
    return handle_request(request, registry, bus)
