import os

PREFIX = "ai_assistant/"

DEFAULTS = {
    "base_url": "",
    "model": "",
    "api_key": "",
    "results_dir": "",
    "port": 8765,
    "verify_ssl": True,
    "max_iterations": 25,
    "explain": True,
    "auto_export": True,
    "language": "auto",
    "window_geometry": "",
}

ENV_NAMES = {
    "base_url": "AI_ASSISTANT_BASE_URL",
    "model": "AI_ASSISTANT_MODEL",
    "api_key": "AI_ASSISTANT_API_KEY",
}

_memory = {}
_prefs = None


def _preferences():
    global _prefs
    if _prefs is not None:
        return _prefs
    try:
        from UM.Application import Application
        app = Application.getInstance()
        prefs = app.getPreferences()
    except Exception:
        return None
    for key, default in DEFAULTS.items():
        prefs.addPreference(PREFIX + key, default)
    _prefs = prefs
    return prefs


def _coerce(key, value):
    default = DEFAULTS[key]
    if isinstance(default, bool):
        if isinstance(value, str):
            return value.strip().lower() in ("1", "true", "yes", "on")
        return bool(value)
    if isinstance(default, int):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
    return "" if value is None else str(value)


def get(key):
    prefs = _preferences()
    if prefs is not None:
        value = _coerce(key, prefs.getValue(PREFIX + key))
    else:
        value = _coerce(key, _memory.get(key, DEFAULTS[key]))
    if value in ("", None) and key in ENV_NAMES:
        env = os.environ.get(ENV_NAMES[key])
        if env:
            return env
    return value


def set_value(key, value):
    if key not in DEFAULTS:
        raise KeyError(key)
    value = _coerce(key, value)
    prefs = _preferences()
    if prefs is not None:
        prefs.setValue(PREFIX + key, value)
    else:
        _memory[key] = value


def mask_key(key):
    if not key:
        return ""
    if len(key) <= 8:
        return "*" * len(key)
    return key[:3] + "..." + key[-4:]


def public_settings():
    return {
        "base_url": get("base_url"),
        "model": get("model"),
        "api_key": mask_key(get("api_key")),
        "api_key_set": bool(get("api_key")),
        "has_key": bool(get("api_key")),
        "explain": get("explain"),
        "auto_export": get("auto_export"),
        "language": get("language"),
        "language_effective": effective_language(),
        "slicer_language": slicer_language(),
        "results_dir": get_results_dir(),
        "port": get("port"),
        "verify_ssl": get("verify_ssl"),
    }


def update_settings(data):
    for key in ("base_url", "model", "results_dir", "port", "verify_ssl", "explain", "auto_export", "language"):
        if key in data:
            set_value(key, data[key])
    key = data.get("api_key")
    if key and "..." not in key and not set(key) == {"*"}:
        set_value("api_key", key.strip())
    return public_settings()


SUPPORTED_LANGUAGES = ("ru", "en")


def slicer_language():
    try:
        from UM.Application import Application
        value = Application.getInstance().getPreferences().getValue("general/language")
    except Exception:
        return ""
    return str(value or "").split("_")[0].lower()


def effective_language():
    chosen = get("language")
    if chosen and chosen != "auto":
        return chosen
    return slicer_language() or "en"


def _config_dir():
    try:
        from UM.Resources import Resources
        return Resources.getStoragePath(Resources.Preferences, "")
    except Exception:
        return os.path.join(os.path.expanduser("~"), ".ai_assistant")


def get_results_dir():
    value = get("results_dir")
    if value:
        return os.path.expanduser(value)
    return os.path.join(os.path.expanduser("~"), "AIAssistantResults")


def get_uploads_dir():
    path = os.path.join(get_results_dir(), "_uploads")
    if not os.path.isdir(path):
        os.makedirs(path)
    return path


def safe_name(name):
    keep = []
    for ch in str(name):
        if ch.isalnum() or ch in " ._-()":
            keep.append(ch)
        else:
            keep.append("_")
    result = "".join(keep).strip(" .")
    return result or "model"


def get_model_dir(model_name):
    path = os.path.join(get_results_dir(), safe_name(model_name))
    if not os.path.isdir(path):
        os.makedirs(path)
    return path
