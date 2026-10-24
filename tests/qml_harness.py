import json
import os
import sys

from PyQt5.QtCore import QObject, QSizeF, QUrl, QtMsgType, pyqtProperty, pyqtSlot, qInstallMessageHandler
from PyQt5.QtGui import QColor, QFont, QFontDatabase, QFontMetrics, QGuiApplication
from PyQt5.QtQml import QQmlComponent, QQmlContext, QQmlEngine, qmlRegisterSingletonType, qmlRegisterType
from PyQt5.QtQuick import QQuickWindow

HERE = os.path.dirname(os.path.abspath(__file__))
STUB_DIR = os.path.join(HERE, "qml_stub")
QML_DIR = os.path.join(os.path.dirname(HERE), "plugin", "AIAssistant", "qml")
DEFAULT_THEME = os.environ.get("STE_THEME_DIR",
                               r"C:\Program Files\Stereotech STE Slicer 7.10\resources\themes\material")

MESSAGES = []
_state = {"app": None, "scale": 1.0, "theme_dir": None, "registered": False}


def _handler(kind, context, message):
    MESSAGES.append((kind, message))


def app(scale=1.0, theme_dir=None):
    if _state["app"] is None:
        if sys.platform != "win32":
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        os.environ.setdefault("QT_QUICK_BACKEND", "software")
        fonts = os.path.join(os.environ.get("WINDIR", "C:" + os.sep + "Windows"), "Fonts")
        if os.path.isdir(fonts):
            os.environ.setdefault("QT_QPA_FONTDIR", fonts)
        qInstallMessageHandler(_handler)
        _state["app"] = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])
        _state["app"].setOrganizationName("Karfogen")
        _state["app"].setOrganizationDomain("karfogen.local")
        _state["app"].setApplicationName("AIAssistantTests")
    font = QFont()
    font.setPointSizeF(9 * scale)
    _state["app"].setFont(font)
    _state["scale"] = scale
    _state["theme_dir"] = theme_dir or DEFAULT_THEME
    _register()
    return _state["app"]


class ThemeStub(QObject):
    def __init__(self, engine, path, parent=None):
        super(ThemeStub, self).__init__(parent)
        self._colors = {}
        self._sizes = {}
        self._fonts = {}
        self._icons = {}
        self._styles = None
        app_font = QGuiApplication.instance().font()
        em = int(QFontMetrics(app_font).ascent())
        theme_file = os.path.join(path or "", "theme.json")
        data = {}
        if os.path.isfile(theme_file):
            with open(theme_file, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            fonts_dir = os.path.join(path, "fonts")
            for folder, _, files in os.walk(fonts_dir):
                for name in files:
                    if name.endswith(".ttf"):
                        QFontDatabase.addApplicationFont(os.path.join(folder, name))
            icons = os.path.join(path, "icons")
            for name in os.listdir(icons):
                self._icons[os.path.splitext(name)[0]] = QUrl.fromLocalFile(os.path.join(icons, name))
        for name, value in data.get("colors", {}).items():
            self._colors[name] = QColor(*value)
        factor = 1.25 if em <= 12 else 1.0
        for name, value in data.get("sizes", {}).items():
            self._sizes[name] = QSizeF(round(value[0] * em * factor), round(value[1] * em * factor))
        for name, spec in data.get("fonts", {}).items():
            font = QFont()
            font.setFamily(spec.get("family", app_font.family()))
            font.setWeight(spec.get("weight", 50))
            font.setItalic(spec.get("italic", False))
            font.setPointSize(int(spec.get("size", 1) * app_font.pointSize()))
            font.setCapitalization(QFont.AllUppercase if spec.get("capitalize") else QFont.MixedCase)
            self._fonts[name] = font
        self._em = em * factor
        styles = os.path.join(path or "", "styles.qml")
        if not os.path.isfile(styles):
            styles = os.path.join(STUB_DIR, "styles.qml")
        component = QQmlComponent(engine, QUrl.fromLocalFile(styles))
        context = QQmlContext(engine.rootContext(), engine)
        context.setContextProperty("Theme", self)
        self._styles = component.create(context)
        if self._styles is None:
            component = QQmlComponent(engine, QUrl.fromLocalFile(os.path.join(STUB_DIR, "styles.qml")))
            self._styles = component.create(context)
        self._styles_context = context
        for error in component.errors():
            MESSAGES.append((QtMsgType.QtWarningMsg, error.toString()))

    @pyqtSlot(str, result=QColor)
    def getColor(self, name):
        return self._colors.get(name, QColor(128, 128, 128))

    @pyqtSlot(str, result="QSizeF")
    def getSize(self, name):
        return self._sizes.get(name, QSizeF(self._em, self._em))

    @pyqtSlot(str, result=QUrl)
    def getIcon(self, name):
        return self._icons.get(name, QUrl())

    @pyqtSlot(str, result=QFont)
    def getFont(self, name):
        return self._fonts.get(name, QGuiApplication.instance().font())

    @pyqtProperty(QObject, constant=True)
    def styles(self):
        return self._styles


def _theme_factory(engine, script_engine):
    theme = ThemeStub(engine, _state["theme_dir"])
    _state.setdefault("themes", []).append(theme)
    return theme


def _register():
    if _state["registered"]:
        return
    _state["registered"] = True
    qmlRegisterSingletonType(ThemeStub, "UM", 1, 0, "Theme", _theme_factory)
    qmlRegisterType(QUrl.fromLocalFile(os.path.join(STUB_DIR, "PointingRectangle.qml")), "UM", 1, 0, "PointingRectangle")
    for minor in (0, 1, 2, 3, 4):
        qmlRegisterType(QUrl.fromLocalFile(os.path.join(STUB_DIR, "RecolorImage.qml")), "UM", 1, minor, "RecolorImage")
        qmlRegisterType(QUrl.fromLocalFile(os.path.join(STUB_DIR, "TooltipArea.qml")), "UM", 1, minor, "TooltipArea")


def engine(scale=1.0):
    if _state.get("engine") is None:
        _state["engine"] = QQmlEngine()
    _state["engine"].rootContext().setContextProperty("screenScaleFactor", scale)
    return _state["engine"]


def create(controller, qml_name="AssistantWindow.qml", scale=1.0):
    engine = globals()["engine"](scale)
    context = QQmlContext(engine.rootContext(), engine)
    context.setContextProperty("assistant", controller)
    component = QQmlComponent(engine, QUrl.fromLocalFile(os.path.join(QML_DIR, qml_name)))
    window = component.create(context)
    if window is not None:
        window.setOpacity(0.0)
        window.setPosition(40, 40)
    errors = [e.toString() for e in component.errors()]
    return engine, context, component, window, errors


KNOWN_QT515_NOTES = ("Implicitly defined onFoo properties in Connections are deprecated",)


def problems():
    bad = []
    for kind, message in MESSAGES:
        if any(note in message for note in KNOWN_QT515_NOTES):
            continue
        if kind in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg):
            if "qml" in message.lower() or "QML" in message or ".qml" in message:
                bad.append(message)
    return bad
