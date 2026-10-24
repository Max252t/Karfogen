import os
import re

MAX_TITLE_CHARS = 48
MAX_TITLE_WORDS = 6
DEFAULT_TITLES = {"ru": "Новый проект", "en": "New project"}

GREETING_WORDS = set("""
привет приветик приветствую здравствуй здравствуйте здорово хай салют добрый доброе доброго день утро вечер ночи
спасибо спасибочки благодарю пасиб спс ок окей ага угу да нет ладно хорошо отлично понятно ясно пожалуйста плиз
как дела делишки ты вы тут там кто что чем умеешь можешь работаешь меня тебя вас зовут пока
hello hi hey hiya greetings good morning afternoon evening night thanks thank thx you ok okay yes no sure fine great
please how are what can do who there bye
""".split())

LEAD_WORDS = set("""
привет приветик здравствуй здравствуйте добрый день вечер утро пожалуйста плиз нужно надо необходимо требуется
хочу хотел хотела хотим бы мне нам нужна нужен нужно нужны давай давайте можешь можете можно помоги помогите
подготовь подготовьте подготовить напечатай напечатайте напечатать распечатай распечатать распечатаем напечатаем
сделай сделайте сделать нарежь нарежьте нарезать настрой настройте настроить подбери подберите подобрать
есть вот это у меня такая такой такое
please hi hello hey i we need want would like to can could you help me prepare print slice make set up setup a an
the this there is it lets let's
""".split())

GENERIC_WORDS = set("""
проект запрос печать печати печатью задача задачу модель модели модель файл файла деталь детали деталью её его это
project request printing print task model file part it this
""".split())

COMPARATIVES = set("stronger better faster smoother bigger smaller thicker thinner lighter cheaper".split())
PARAMETER_WORDS = set("""
модуль диаметр размер размером размеры толщина толщиной высота высотой длина длиной ширина шириной масштаб
module diameter size thickness height length width scale
""".split())

BREAK_WORDS = set("""
чтобы который которая которое которые потому так если но а и или где когда что
which that so because if but and or where when
""".split())

DROP_WORDS = set("для a an the".split())
TRAILING_WORDS = set("из для с со на в во по под к о и или of for with in on at from to and or by".split())
SERVICE_PHRASES = (r"\b(для|к|на)\s+печати\b", r"\bна\s+печать\b", r"\bfor\s+printing\b", r"\bto\s+print\b",
                   r"\bдля\s+3d[- ]?печати\b", r"\bfor\s+3d[- ]?printing\b")
NOTE_PREFIXES = ("Прикреплён файл", "Прикреплено изображение", "Модель уже в сцене", "Режим печати зафиксирован",
                 "Имя результата", "Язык ответа", "Reply language", "[изображения", "Изображение ")
MATERIALS = ("PETG", "PLA", "ABS", "ASA", "TPU", "TPE", "PA12", "PA6", "PA", "PC", "PP", "CPE+", "CPE", "HIPS", "PVA",
             "Nylon", "нейлон")
FILE_NOISE = re.compile(r"^(v\d+[a-z]?|ver\d*|rev\d*|r\d+|final|finale|fixed|fix|new|old|copy|copia|test|tmp|temp|"
                        r"draft|export|\d+|\d+mm|[0-9a-f]{8,})$", re.IGNORECASE)
WORD = re.compile(r"[0-9A-Za-zА-Яа-яЁё+](?:[0-9A-Za-zА-Яа-яЁё+\-]|[.,](?=\d))*")


def _words(text):
    return WORD.findall(text or "")


def clean_request_text(text):
    lines = []
    for line in str(text or "").replace("\r\n", "\n").split("\n"):
        if line.strip().startswith(NOTE_PREFIXES):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def is_contentless(text):
    words = [w.lower() for w in _words(text)]
    meaningful = [w for w in words if w not in GREETING_WORDS and w not in LEAD_WORDS and len(w) > 1]
    return not meaningful


def _material(text):
    for name in MATERIALS:
        if re.search(r"(?<![\w+])%s(?![\w+])" % re.escape(name), text, re.IGNORECASE):
            return name.upper() if re.match(r"^[A-Za-z0-9+]+$", name) else name
    return ""


def _nominative(words):
    result = list(words)
    for index, word in enumerate(result):
        lower = word.lower()
        if lower.endswith(("ую", "юю")):
            result[index] = word[:-2] + ("ая" if lower.endswith("ую") else "яя")
            continue
        if re.search(r"[А-Яа-яЁё]", word):
            if lower.endswith("ю") and len(word) > 3:
                result[index] = word[:-1] + "я"
            elif lower.endswith("у") and len(word) > 3:
                result[index] = word[:-1] + "а"
        break
    return result


def _limit(words):
    words = list(words[:MAX_TITLE_WORDS])
    while words and len(" ".join(words)) > MAX_TITLE_CHARS:
        words.pop()
    while words and words[-1].lower() in TRAILING_WORDS:
        words.pop()
    return words


def _capitalize(text):
    return text[:1].upper() + text[1:] if text else text


def _phrase(sentence):
    text = sentence
    for pattern in SERVICE_PHRASES:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)
    for chunk in re.split(r"[,;:()\[\]—–]|\s-\s", text):
        phrase = _chunk_phrase(chunk)
        if phrase:
            return phrase
    return []


def _chunk_phrase(chunk):
    words = _words(chunk)
    while words and words[0].lower() in LEAD_WORDS | GREETING_WORDS:
        words.pop(0)
    phrase = []
    for word in words:
        lower = word.lower()
        if lower in BREAK_WORDS or lower in PARAMETER_WORDS or (re.search(r"\d", word) and not _material(word)):
            break
        if lower in DROP_WORDS:
            continue
        phrase.append(word)
    while phrase and phrase[0].lower() in GENERIC_WORDS:
        phrase.pop(0)
    if not phrase or is_contentless(" ".join(phrase)):
        return []
    head = phrase[0].lower()
    if head in COMPARATIVES or (re.search(r"[а-яё]", head) and head.endswith(("ее", "ей"))):
        return []
    return _nominative(phrase)


def title_from_file(name):
    base = os.path.splitext(os.path.basename(str(name or "")))[0]
    base = re.sub(r"([a-zа-яё])([A-ZА-ЯЁ])", r"\1 \2", base)
    parts = [p for p in re.split(r"[\s_.\-]+", base) if p and not FILE_NOISE.match(p)]
    words = _limit(parts)
    return _capitalize(" ".join(words)) if words else None


def title_from_text(text, language="ru"):
    text = clean_request_text(text)
    if not text or is_contentless(text):
        return None
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", text):
        phrase = _phrase(sentence)
        if not phrase:
            continue
        material = _material(text)
        russian = bool(re.search(r"[А-Яа-яЁё]", " ".join(phrase)))
        lowered = [w.lower() for w in phrase]
        if material and not russian and material.lower() in lowered:
            at = lowered.index(material.lower())
            start = at - 1 if at > 0 and lowered[at - 1] in ("in", "from", "of", "made") else at
            phrase = phrase[:start] + phrase[at + 1:]
            lowered = [w.lower() for w in phrase]
        if material and material.lower() not in lowered and len(phrase) < MAX_TITLE_WORDS - 1:
            if russian:
                phrase = phrase + ["из", material]
            else:
                first = phrase[0] if phrase[0].isupper() else phrase[0][:1].lower() + phrase[0][1:]
                phrase = [material, first] + phrase[1:]
        words = _limit(phrase)
        if words:
            return _capitalize(" ".join(words))
    return None


def suggest_title(text, files=None, language="ru"):
    title = title_from_text(text, language)
    if title:
        return title
    if is_contentless(clean_request_text(text)) and not files:
        return None
    for name in files or []:
        title = title_from_file(name)
        if title:
            return title
    return None


def sanitize_title(title):
    text = str(title or "").strip().strip("\"'«»„“”`").strip()
    text = " ".join(w for w in text.split() if not re.search(r"[\\/]", w))
    text = re.sub(r"\.(stl|obj|3mf|gcode|png|jpe?g)\b", "", text, flags=re.IGNORECASE)
    text = text.rstrip(" .!?,;:")
    words = text.split()
    while words and words[0].lower().strip(":") in GENERIC_WORDS:
        words.pop(0)
    words = _limit(words)
    text = " ".join(words)
    if not text or is_contentless(text):
        return None
    return _capitalize(text)


def finished_requests(events):
    requests = []
    pending = None
    for event in events or []:
        kind = event.get("type")
        data = event.get("data") or {}
        if kind == "user_message":
            pending = {"text": data.get("text") or "", "files": [f.get("name", "") for f in data.get("files") or []]
                       + list(data.get("scene") or [])}
        elif kind == "done" and pending is not None:
            requests.append(pending)
            pending = None
    return requests


def title_from_events(events, language="ru", ignored=()):
    for request in finished_requests(events):
        if request["text"].strip() in ignored:
            continue
        title = suggest_title(request["text"], request["files"], language)
        if title:
            return title
    return None
