import os
import time
import unittest

import support

try:
    import qml_harness
    from PyQt5.QtCore import QObject, QUrl, pyqtProperty
    from PyQt5.QtQml import QQmlComponent, QQmlContext
    HAVE_QT = True
except ImportError:
    HAVE_QT = False

QML_URL = "file:///" + os.path.join(support.ROOT, "plugin", "AIAssistant", "qml").replace(os.sep, "/")

CONFIRM = u"""
import QtQuick 2.2
import "%s"
ConfirmDialog {
    title: "Создать новый проект?"
    message: "Текущий проект сохранится."
    confirmText: "Создать"
    checkText: "Очистить сцену и сбросить изменения настроек"
    checkHint: "Модели будут удалены из сцены, а настройки вернутся к профилю — чтобы прошлые настройки не попали в новую деталь."
    checked: true
}
""" % QML_URL

RENAME = u"""
import QtQuick 2.2
import "%s"
RenameDialog {}
""" % QML_URL

if HAVE_QT:
    class Assistant(QObject):
        @pyqtProperty("QVariantMap", constant=True)
        def strings(self):
            return {"cancel": "Отмена", "save": "Сохранить", "proj_rename_title": "Переименовать проект",
                    "proj_rename_hint": "Новое название"}


def pump(app, rounds=40):
    for _ in range(rounds):
        app.processEvents()
        time.sleep(0.01)


def children_of(item, class_prefix):
    return [child for child in item.childItems() if child.metaObject().className().startswith(class_prefix)]


@unittest.skipUnless(HAVE_QT, "PyQt5 is required to load the QML")
class DialogLayoutTest(unittest.TestCase):
    def tearDown(self):
        qml_harness.app(1.0)
        qml_harness.engine(1.0)
        del qml_harness.MESSAGES[:]

    def open_dialog(self, source, scale, ask_args=()):
        app = qml_harness.app(scale)
        engine = qml_harness.engine(scale)
        assistant = Assistant()
        context = QQmlContext(engine.rootContext(), engine)
        context.setContextProperty("assistant", assistant)
        component = QQmlComponent(engine)
        component.setData(source.encode("utf-8"), QUrl(QML_URL + "/Probe.qml"))
        window = component.create(context)
        self.assertIsNotNone(window, [e.toString() for e in component.errors()])
        window.ask(*ask_args)
        pump(app)
        self.addCleanup(window.close)
        self.keep = (assistant, context, component, engine)
        return window

    def assert_buttons_below_content(self, window):
        root = window.contentItem().childItems()[0]
        body = children_of(root, "QQuickColumn")[0]
        buttons = children_of(root, "QQuickRow")[0]
        self.assertGreaterEqual(buttons.y(), body.y() + body.height())
        self.assertGreaterEqual(window.height(), buttons.y() + buttons.height())
        self.assertEqual(window.height(), window.property("contentHeight"))
        self.assertEqual(window.minimumHeight(), window.maximumHeight())

    def test_confirm_dialog_keeps_buttons_below_the_text_at_every_scale(self):
        for scale in (1.0, 1.25, 1.5, 2.0):
            window = self.open_dialog(CONFIRM, scale)
            self.assert_buttons_below_content(window)
            window.close()

    def test_check_row_includes_its_label_offset(self):
        window = self.open_dialog(CONFIRM, 1.25)
        root = window.contentItem().childItems()[0]
        body = children_of(root, "QQuickColumn")[0]
        row = [item for item in body.childItems() if item.metaObject().className().startswith("CheckRow")][0]
        labels = children_of(row, "QQuickColumn")[0]
        self.assertGreaterEqual(row.height(), labels.y() + labels.height())

    def test_rename_dialog_follows_its_content(self):
        window = self.open_dialog(RENAME, 1.5, ("Колесо",))
        self.assertEqual(window.height(), window.property("contentHeight"))
        self.assertEqual(window.minimumHeight(), window.maximumHeight())


if __name__ == "__main__":
    unittest.main()
