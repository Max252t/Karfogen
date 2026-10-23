import base64
import binascii
import os
import threading
import uuid

from .. import config

MAX_BYTES = 100 * 1024 * 1024
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png")
MODEL_EXTENSIONS = (".stl", ".obj", ".3mf")
MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
MAX_IMAGE_SIDE = 1568
MAX_RAW_IMAGE_BYTES = 5 * 1024 * 1024

_lock = threading.Lock()
_items = {}


class UploadError(Exception):
    pass


def save_upload(name, data_base64):
    if not name:
        raise UploadError("Не указано имя файла")
    ext = os.path.splitext(name)[1].lower()
    if ext in IMAGE_EXTENSIONS:
        kind = "image"
    elif ext in MODEL_EXTENSIONS:
        kind = "model"
    else:
        raise UploadError("Неподдерживаемый тип файла. Разрешены: JPG, PNG, STL, OBJ, 3MF")
    if "," in data_base64[:100] and data_base64.startswith("data:"):
        data_base64 = data_base64.split(",", 1)[1]
    try:
        data = base64.b64decode(data_base64)
    except (binascii.Error, ValueError):
        raise UploadError("Некорректные данные файла")
    if len(data) > MAX_BYTES:
        raise UploadError("Файл больше 100 МБ")
    with _lock:
        item_id = "f" + uuid.uuid4().hex[:12]
        folder = os.path.join(config.get_uploads_dir(), item_id)
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, config.safe_name(name))
        with open(path, "wb") as handle:
            handle.write(data)
        item = {"id": item_id, "name": name, "kind": kind, "path": path, "size": len(data)}
        _items[item_id] = item
    return item


def get_item(item_id):
    return _items.get(item_id)


def _encode_with_qt(path):
    from PyQt5.QtCore import QBuffer, QByteArray, QIODevice, Qt
    from PyQt5.QtGui import QImage
    image = QImage(path)
    if image.isNull():
        return None
    if max(image.width(), image.height()) > MAX_IMAGE_SIDE:
        image = image.scaled(MAX_IMAGE_SIDE, MAX_IMAGE_SIDE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    fmt, mime = ("PNG", "image/png") if image.hasAlphaChannel() else ("JPEG", "image/jpeg")
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.WriteOnly)
    if not image.save(buffer, fmt, 85):
        return None
    return mime, bytes(data)


def image_data_url(item):
    try:
        encoded = _encode_with_qt(item["path"])
    except Exception:
        encoded = None
    if encoded is None:
        if os.path.getsize(item["path"]) > MAX_RAW_IMAGE_BYTES:
            return None
        ext = os.path.splitext(item["path"])[1].lower()
        with open(item["path"], "rb") as handle:
            encoded = (MIME.get(ext, "image/png"), handle.read())
    return "data:%s;base64,%s" % (encoded[0], base64.b64encode(encoded[1]).decode("ascii"))
