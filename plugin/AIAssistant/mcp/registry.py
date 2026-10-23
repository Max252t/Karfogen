import time
import traceback


class ToolError(Exception):
    pass


class Tool(object):
    def __init__(self, name, description, input_schema, handler):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.handler = handler


_TYPE_MAP = {
    "string": (str,),
    "integer": (int,),
    "number": (int, float),
    "boolean": (bool,),
    "array": (list,),
    "object": (dict,),
}


def _check_type(value, expected):
    types = _TYPE_MAP.get(expected)
    if types is None:
        return True
    if expected in ("integer", "number") and isinstance(value, bool):
        return False
    if expected == "integer" and isinstance(value, float):
        return value == int(value)
    return isinstance(value, types)


def validate_arguments(schema, arguments):
    if not isinstance(arguments, dict):
        raise ToolError("arguments must be an object")
    props = schema.get("properties", {})
    for name in schema.get("required", []):
        if name not in arguments or arguments[name] is None:
            raise ToolError("Missing required argument: %s" % name)
    result = {}
    for name, value in arguments.items():
        spec = props.get(name)
        if spec is None or value is None:
            continue
        expected = spec.get("type")
        if isinstance(expected, list):
            if not any(_check_type(value, t) for t in expected):
                raise ToolError("Argument '%s' has wrong type, expected %s" % (name, "/".join(expected)))
        elif expected and not _check_type(value, expected):
            raise ToolError("Argument '%s' has wrong type, expected %s" % (name, expected))
        if expected == "integer" and isinstance(value, float):
            value = int(value)
        enum = spec.get("enum")
        if enum is not None and value not in enum:
            raise ToolError("Argument '%s' must be one of: %s" % (name, ", ".join(str(e) for e in enum)))
        result[name] = value
    return result


class ToolRegistry(object):
    def __init__(self):
        self._tools = {}
        self._order = []

    def register(self, name, description, input_schema, handler):
        if name not in self._tools:
            self._order.append(name)
        self._tools[name] = Tool(name, description, input_schema, handler)

    def tool(self, name, description, properties=None, required=None):
        schema = {"type": "object", "properties": properties or {}}
        if required:
            schema["required"] = list(required)

        def decorator(func):
            self.register(name, description, schema, func)
            return func
        return decorator

    def has(self, name):
        return name in self._tools

    def get(self, name):
        return self._tools.get(name)

    def names(self):
        return list(self._order)

    def list_mcp(self):
        return [{"name": t.name, "description": t.description, "inputSchema": t.input_schema}
                for t in (self._tools[n] for n in self._order)]

    def list_openai(self):
        return [{"type": "function",
                 "function": {"name": t.name, "description": t.description, "parameters": t.input_schema}}
                for t in (self._tools[n] for n in self._order)]

    def call(self, name, arguments):
        tool = self._tools[name]
        args = validate_arguments(tool.input_schema, arguments or {})
        return tool.handler(args)


_registry = ToolRegistry()


def get_registry():
    return _registry


def _log_error(text):
    try:
        from UM.Logger import Logger
        Logger.log("e", "AIAssistant: " + text)
    except Exception:
        pass


def run_guarded(registry, name, arguments):
    started = time.time()
    try:
        result = registry.call(name, arguments)
        return True, result, int((time.time() - started) * 1000)
    except ToolError as e:
        return False, str(e), int((time.time() - started) * 1000)
    except Exception as e:
        _log_error("tool %s failed: %s" % (name, traceback.format_exc()))
        return False, "%s: %s" % (e.__class__.__name__, e), int((time.time() - started) * 1000)
