import webbrowser

from UM.Extension import Extension
from UM.Logger import Logger

from .server.http_server import AssistantServer
from .tools import register_all


class AIAssistant(Extension):
    def __init__(self):
        super().__init__()
        self._server = AssistantServer()
        self.setMenuName("AI Assistant")
        self.addMenuItem("Open chat", self.openChat)
        try:
            register_all()
        except Exception:
            Logger.logException("e", "AIAssistant: failed to register tools")
        try:
            self._server.start()
        except Exception:
            Logger.logException("e", "AIAssistant: failed to start server")

    def openChat(self):
        if self._server.port is None:
            self._server.start()
        url = self._server.url()
        Logger.log("i", "AIAssistant: opening %s" % url)
        webbrowser.open(url)
