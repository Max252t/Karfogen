import os

from UM.Application import Application
from UM.Extension import Extension
from UM.Logger import Logger

from .agent.agent import get_agent
from .server import projects
from .server.events import get_bus
from .server.http_server import AssistantServer
from .tools import register_all

QML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qml", "AssistantWindow.qml")


class AIAssistant(Extension):
    def __init__(self):
        super().__init__()
        self._server = AssistantServer()
        self._controller = None
        self._window = None
        self.setMenuName("AI Assistant")
        self.addMenuItem("Open chat", self.openChat)
        try:
            register_all()
        except Exception:
            Logger.logException("e", "AIAssistant: failed to register tools")
        projects.get_manager().attach(get_agent(), get_bus())
        try:
            self._server.start()
        except Exception:
            Logger.logException("e", "AIAssistant: failed to start MCP server")
        try:
            Application.getInstance().applicationShuttingDown.connect(self._shutdown)
            Application.getInstance().mainWindowChanged.connect(self._watch_slicing)
        except Exception:
            Logger.logException("w", "AIAssistant: could not subscribe to application signals")

    def _watch_slicing(self):
        from .tools import slice_tools
        try:
            slice_tools.attach_monitor()
        except Exception:
            Logger.logException("w", "AIAssistant: slicing done in the slicer UI will be detected on first export")

    def openChat(self):
        if self._window is None:
            self._create_window()
        if self._window is None:
            return
        self._window.show()
        self._window.raise_()
        self._window.requestActivate()

    def _create_window(self):
        from .ui.controller import NativeChatController
        app = Application.getInstance()
        controller = NativeChatController()
        window = app.createQmlComponent(QML_PATH, {"assistant": controller})
        if window is None:
            Logger.log("e", "AIAssistant: could not create the chat window, see QML errors above")
            controller.stop()
            return
        controller.setWindow(window)
        main = app.getMainWindow()
        if main is not None:
            window.setTransientParent(main)
            if not controller.windowGeometry:
                margin = int(24 * main.devicePixelRatio())
                window.setX(main.x() + max(0, main.width() - window.width() - margin))
                window.setY(main.y() + margin * 3)
        try:
            app.getController().getScene().sceneChanged.connect(controller.markSceneDirty)
        except Exception:
            Logger.logException("w", "AIAssistant: scene changes will not be tracked")
        self._controller = controller
        self._window = window

    def _shutdown(self):
        if self._controller is not None:
            self._controller.stop()
        agent = get_agent()
        if agent.is_running():
            agent.cancel()
        try:
            projects.get_manager().save_current()
        finally:
            try:
                self._server.stop()
            except Exception:
                Logger.logException("w", "AIAssistant: MCP server did not stop cleanly")
