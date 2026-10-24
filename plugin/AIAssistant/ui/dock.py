from PyQt5.QtCore import QObject, QRect, Qt, QTimer

from .dock_layout import (DEFAULT_SHARE, MAIN_PREFS, MAX_SHARE, MIN_SHARE, SETTLE_MS, clamp_share, close, dock_layout,
                          grow, share_from_legacy, visible_edges, user_share)


class DockManager(QObject):
    def __init__(self, main, panel, prefs=None, settings=None, parent=None):
        super(DockManager, self).__init__(parent)
        self._main = main
        self._panel = panel
        self._prefs = prefs
        self._settings = settings
        self._active = False
        self._tiled = False
        self._applying = False
        self._snapshot = None
        self._expected = None
        self._sources = set()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(SETTLE_MS)
        self._timer.timeout.connect(self._settle)
        for name, window in (("main", main), ("panel", panel)):
            for signal in (window.xChanged, window.yChanged, window.widthChanged, window.heightChanged,
                           window.windowStateChanged, window.screenChanged):
                signal.connect(lambda *args, source=name: self._changed(source))
        panel.visibleChanged.connect(self._visibility)

    @property
    def active(self):
        return self._active

    def _setting(self, key, value=None):
        if self._settings is None:
            return None
        if value is None:
            return self._settings.get(key)
        self._settings.set_value(key, value)
        return value

    def share(self):
        stored = self._setting("panel_share")
        if stored:
            try:
                value = float(stored)
            except (TypeError, ValueError):
                value = DEFAULT_SHARE
            if value < MIN_SHARE or value > MAX_SHARE or value != value:
                value = DEFAULT_SHARE
                self._store_share(value)
            return clamp_share(value)
        legacy = self._setting("window_geometry")
        share = DEFAULT_SHARE
        if legacy:
            migrated = share_from_legacy(legacy, self._available()[2])
            self._setting("window_geometry", "")
            if migrated is not None:
                share = clamp_share(migrated)
                self._store_share(share)
        return share

    def _store_share(self, share):
        self._setting("panel_share", "%.4f" % clamp_share(share))
        persist = getattr(self._settings, "persist", None)
        if persist is not None:
            persist()

    def _available(self):
        screen = self._main.screen()
        rect = screen.availableGeometry()
        return (rect.x(), rect.y(), rect.width(), rect.height())

    def _edges(self, window):
        edges = visible_edges(window) if window.isVisible() else None
        if edges is None:
            margins = window.frameMargins()
            edges = (margins.left(), margins.top(), margins.right(), margins.bottom())
        return edges

    def _frame(self, window):
        rect = window.geometry()
        return grow((rect.x(), rect.y(), rect.width(), rect.height()), self._edges(window))

    def open(self):
        if self._active and self._panel.isVisible():
            self._panel.raise_()
            self._panel.requestActivate()
            return
        if not self._active:
            self._snapshot = self._capture()
        self._panel.show()
        self._active = True
        self._apply(self.share())
        self._panel.raise_()
        self._panel.requestActivate()

    def _capture(self):
        main = self._main
        rect = main.geometry()
        state = int(main.windowState())
        normal = (rect.x(), rect.y(), rect.width(), rect.height())
        if state & int(Qt.WindowMaximized) and self._prefs is not None:
            try:
                normal = tuple(int(self._prefs.getValue(key)) for key in MAIN_PREFS)
            except (TypeError, ValueError):
                pass
        return {"state": state, "normal": normal}

    def _visibility(self, visible):
        if not visible and self._active:
            self.restore()

    def restore(self):
        if not self._active:
            return
        self._active = False
        tiled = self._tiled
        self._tiled = False
        self._timer.stop()
        self._sources = set()
        self._expected = None
        snapshot = self._snapshot
        self._snapshot = None
        if snapshot is None or not tiled:
            return
        self._restore_main(snapshot)

    def _restore_main(self, snapshot, panel_geometry=None):
        self._applying = True
        try:
            self._main.setGeometry(QRect(*snapshot["normal"]))
            if snapshot["state"] & int(Qt.WindowMaximized):
                self._main.showMaximized()
            else:
                self._main.showNormal()
                self._main.setGeometry(QRect(*snapshot["normal"]))
            if panel_geometry is not None:
                self._panel.setGeometry(panel_geometry)
        finally:
            self._applying = False
        self._write_prefs(snapshot)

    def release(self):
        if self._tiled:
            self._write_prefs(self._snapshot)
        self._active = False
        self._tiled = False
        self._timer.stop()
        self._sources = set()

    def _changed(self, source):
        if not self._active or not self._tiled or self._applying:
            return
        self._sources.add(source)
        self._timer.start()

    def _minimized(self, window):
        return bool(int(window.windowState()) & int(Qt.WindowMinimized))

    def _settle(self):
        sources = self._sources
        self._sources = set()
        if not self._active or not self._tiled or self._minimized(self._main) or self._minimized(self._panel):
            return
        available = self._available()
        expected = self._expected
        main_frame = self._frame(self._main)
        panel_frame = self._frame(self._panel)
        maximized = int(self._main.windowState()) & int(Qt.WindowMaximized | Qt.WindowFullScreen)
        if expected is not None and not maximized and expected["available"] == available and \
                close(main_frame, expected["main_frame"]) and close(panel_frame, expected["panel_frame"]):
            self._write_prefs(self._snapshot)
            return
        share = user_share(available, sources, main_frame, panel_frame, expected) \
            if not maximized and expected is not None and expected["available"] == available else None
        if share is not None:
            self._store_share(share)
            self._apply(share)
            return
        self._detach(sources)

    def _detach(self, sources):
        snapshot = self._snapshot
        panel_geometry = self._panel.geometry()
        self._tiled = False
        self._expected = None
        self._sources = set()
        self._timer.stop()
        if "panel" in sources and snapshot is not None:
            self._restore_main(snapshot, panel_geometry)
        else:
            self._snapshot = None

    def _apply(self, share):
        available = self._available()
        self._tiled = True
        self._applying = True
        try:
            if int(self._main.windowState()) & int(Qt.WindowMaximized | Qt.WindowFullScreen):
                self._main.showNormal()
            layout = dock_layout(available, share, self._panel.minimumWidth(), self._main.minimumWidth(),
                                 self._edges(self._main), self._edges(self._panel))
            self._main.setGeometry(QRect(*layout["main"]))
            self._panel.setGeometry(QRect(*layout["panel"]))
        finally:
            self._applying = False
        layout["available"] = available
        self._expected = layout
        self._timer.start()

    def _write_prefs(self, snapshot):
        if self._prefs is None or snapshot is None:
            return
        for key, value in zip(MAIN_PREFS, snapshot["normal"]):
            self._prefs.setValue(key, int(value))
        maximized = snapshot["state"] & int(Qt.WindowMaximized)
        self._prefs.setValue("general/window_state", int(Qt.WindowMaximized if maximized else Qt.WindowNoState))

    def layout(self):
        return self._expected
