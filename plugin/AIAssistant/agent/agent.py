import json
import threading
import traceback

from .. import config
from ..mcp import protocol
from ..mcp.registry import get_registry
from ..server import uploads
from ..server.events import get_bus
from . import llm_client, prompts

MAX_TOOL_RESULT_CHARS = 8000
OLD_TOOL_RESULT_CHARS = 400
MAX_HISTORY_CHARS = 120000


def _message_size(message):
    content = message.get("content")
    if isinstance(content, list):
        size = sum(len(part.get("text", "")) for part in content if part.get("type") == "text")
    else:
        size = len(content or "")
    return size + len(json.dumps(message.get("tool_calls") or [], ensure_ascii=False))


def _compact_old(message):
    role = message.get("role")
    content = message.get("content")
    if role == "tool" and content and len(content) > OLD_TOOL_RESULT_CHARS:
        compact = dict(message)
        compact["content"] = content[:OLD_TOOL_RESULT_CHARS] + "...[сокращено]"
        return compact
    if role == "user" and isinstance(content, list):
        compact = dict(message)
        texts = [part.get("text", "") for part in content if part.get("type") == "text"]
        compact["content"] = "\n".join(texts) + "\n[изображения из прошлых сообщений опущены]"
        return compact
    return message


def compact_history(history):
    turns = []
    for message in history:
        if message.get("role") == "user" or not turns:
            turns.append([])
        turns[-1].append(message)
    if not turns:
        return []
    old = [[_compact_old(m) for m in turn] for turn in turns[:-1]]
    current = turns[-1]
    total = sum(_message_size(m) for turn in old + [current] for m in turn)
    while old and total > MAX_HISTORY_CHARS:
        dropped = old.pop(0)
        total -= sum(_message_size(m) for m in dropped)
    return [m for turn in old for m in turn] + current


def _log(level, text):
    try:
        from UM.Logger import Logger
        Logger.log(level, "AIAssistant: " + text)
    except Exception:
        pass


class Agent(object):
    def __init__(self, registry=None, bus=None, llm=None):
        self._registry = registry or get_registry()
        self._bus = bus or get_bus()
        self._llm = llm or llm_client
        self._history = []
        self._lock = threading.Lock()
        self._running = False
        self._thread = None

    def reset(self):
        with self._lock:
            if self._running:
                return False
            self._history = []
        self._bus.clear()
        return True

    def is_running(self):
        return self._running

    def submit(self, text, attachment_ids=None, model_name=None):
        with self._lock:
            if self._running:
                return False, "Ассистент ещё обрабатывает предыдущее сообщение"
            self._running = True
        self._bus.publish("user_message", {"text": text, "attachments": list(attachment_ids or []),
                                           "model_name": model_name})
        self._thread = threading.Thread(target=self._run, args=(text, attachment_ids or [], model_name),
                                        name="AIAssistantAgent")
        self._thread.daemon = True
        self._thread.start()
        return True, "ok"

    def _build_user_message(self, text, attachment_ids, model_name, with_images=True):
        notes = []
        images = []
        for item_id in attachment_ids:
            item = uploads.get_item(item_id)
            if item is None:
                continue
            if item["kind"] == "image":
                notes.append("Прикреплено изображение: %s" % item["name"])
                images.append(item)
            else:
                notes.append("Прикреплён файл: %s, путь: %s" % (item["name"], item["path"]))
        if model_name:
            notes.append("Имя результата (model_name): %s" % model_name)
        full_text = text
        if notes:
            full_text = text + "\n\n" + "\n".join(notes)
        if images and with_images:
            parts = [{"type": "text", "text": full_text}]
            for item in images:
                parts.append({"type": "image_url", "image_url": {"url": uploads.image_data_url(item)}})
            return {"role": "user", "content": parts}
        return {"role": "user", "content": full_text}

    def _status(self, text):
        self._bus.publish("status", {"text": text})

    def _chat(self, messages, tools):
        self._status("Жду ответ LLM")
        return self._llm.chat(messages, tools)

    def _run(self, text, attachment_ids, model_name):
        try:
            has_images = any((uploads.get_item(i) or {}).get("kind") == "image" for i in attachment_ids)
            message = self._build_user_message(text, attachment_ids, model_name)
            self._history.append(message)
            self._loop(has_images, attachment_ids, model_name, text)
        except llm_client.LLMError as e:
            self._bus.publish("error", {"message": str(e)})
        except Exception as e:
            _log("e", traceback.format_exc())
            self._bus.publish("error", {"message": "Внутренняя ошибка ассистента: %s" % e})
        finally:
            self._status("Готово")
            with self._lock:
                self._running = False

    def _messages(self):
        return [{"role": "system", "content": prompts.system_prompt()}] + compact_history(self._history)

    def _loop(self, has_images, attachment_ids, model_name, text):
        tools = self._registry.list_openai()
        limit = config.get("max_iterations")
        for _ in range(limit):
            try:
                reply = self._chat(self._messages(), tools)
            except llm_client.LLMError as e:
                if has_images and e.status in (400, 415, 422):
                    self._history[self._first_user_index()] = \
                        self._build_user_message(text, attachment_ids, model_name, with_images=False)
                    has_images = False
                    self._bus.publish("error", {"message": "Модель не приняла изображения, продолжаю без них."})
                    continue
                raise
            tool_calls = reply.get("tool_calls") or []
            entry = {"role": "assistant", "content": reply.get("content") or ""}
            if tool_calls:
                entry["tool_calls"] = tool_calls
            self._history.append(entry)
            if not tool_calls:
                self._bus.publish("assistant_message", {"text": reply.get("content") or ""})
                return
            if reply.get("content"):
                self._bus.publish("assistant_message", {"text": reply["content"], "intermediate": True})
            for call in tool_calls:
                self._history.append(self._execute(call))
        self._bus.publish("error", {"message": "Достигнут лимит шагов (%d). Уточните запрос или продолжите диалог." % limit})

    def _first_user_index(self):
        for index in range(len(self._history) - 1, -1, -1):
            msg = self._history[index]
            if msg["role"] == "user" and isinstance(msg["content"], list):
                return index
        return 0

    def _execute(self, call):
        function = call.get("function") or {}
        name = function.get("name", "")
        raw_args = function.get("arguments") or "{}"
        try:
            args = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args)
            if not isinstance(args, dict):
                raise ValueError("arguments must be an object")
        except ValueError as e:
            return {"role": "tool", "tool_call_id": call.get("id"),
                    "content": "Некорректные аргументы инструмента: %s" % e}
        self._status("Выполняю инструмент: %s" % name)
        if not self._registry.has(name):
            return {"role": "tool", "tool_call_id": call.get("id"), "content": "Неизвестный инструмент: %s" % name}
        result = protocol.call_tool(name, args, self._registry, self._bus)
        text = "".join(part.get("text", "") for part in result["content"])
        if result["isError"]:
            text = "ОШИБКА: " + text
        if len(text) > MAX_TOOL_RESULT_CHARS:
            text = text[:MAX_TOOL_RESULT_CHARS] + "...[обрезано]"
        return {"role": "tool", "tool_call_id": call.get("id"), "content": text}


_agent = Agent()


def get_agent():
    return _agent
