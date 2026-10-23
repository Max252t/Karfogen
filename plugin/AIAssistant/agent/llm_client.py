import json
import os
import ssl
import time
import urllib.error
import urllib.request

from .. import config


class LLMError(Exception):
    def __init__(self, message, status=None):
        super(LLMError, self).__init__(message)
        self.status = status


CERTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "certs")


def _certifi_bundle():
    try:
        import certifi
        path = certifi.where()
        return path if os.path.isfile(path) else None
    except Exception:
        return None


def _ssl_context():
    context = ssl.create_default_context()
    if not config.get("verify_ssl"):
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context
    bundle = _certifi_bundle()
    if bundle:
        context.load_verify_locations(cafile=bundle)
    if os.path.isdir(CERTS_DIR):
        for name in sorted(os.listdir(CERTS_DIR)):
            if name.endswith(".pem"):
                context.load_verify_locations(cafile=os.path.join(CERTS_DIR, name))
    return context


def _status_message(status, detail):
    if status == 401 or status == 403:
        return "Ключ API отклонён (HTTP %s). Проверьте ключ в настройках." % status
    if status == 404:
        return "Адрес или модель не найдены (HTTP 404). Проверьте URL и название модели."
    if status == 429:
        return "Превышен лимит запросов к LLM (HTTP 429). Повторите позже."
    return "Ошибка LLM (HTTP %s): %s" % (status, detail)


def _endpoint():
    base = config.get("base_url").strip().rstrip("/")
    if not base:
        raise LLMError("Не задан URL API LLM. Укажите его в настройках плагина.")
    return base + "/chat/completions"


def chat(messages, tools=None, timeout=120, retries=2, extra=None):
    key = config.get("api_key")
    model = config.get("model")
    if not key:
        raise LLMError("Не задан ключ API. Укажите его в настройках плагина.")
    if not model:
        raise LLMError("Не задана модель LLM. Укажите её в настройках плагина.")
    body = {"model": model, "messages": messages, "temperature": 0.2}
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"
    if extra:
        body.update(extra)
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    url = _endpoint()
    last_error = None
    for attempt in range(retries + 1):
        request = urllib.request.Request(url, data=payload, method="POST")
        request.add_header("Authorization", "Bearer " + key)
        request.add_header("Content-Type", "application/json")
        try:
            response = urllib.request.urlopen(request, timeout=timeout, context=_ssl_context())
            raw = response.read().decode("utf-8")
            data = json.loads(raw)
            choices = data.get("choices") or []
            if not choices:
                raise LLMError("Пустой ответ LLM: %s" % raw[:300])
            return choices[0]["message"]
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = e.read().decode("utf-8", "replace")[:500]
            except Exception:
                pass
            last_error = LLMError(_status_message(e.code, detail), e.code)
            if e.code < 500:
                raise last_error
        except (urllib.error.URLError, OSError, ValueError) as e:
            last_error = LLMError("LLM недоступна: %s" % getattr(e, "reason", e))
        except LLMError:
            raise
        if attempt < retries:
            time.sleep(1.5 * (attempt + 1))
    raise last_error


def test_connection():
    message = chat([{"role": "user", "content": "Ответь одним словом: ok"}], timeout=30, retries=0,
                   extra={"max_tokens": 16})
    return (message.get("content") or "").strip()
