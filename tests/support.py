import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN_DIR = os.path.join(ROOT, "plugin", "AIAssistant")


def install_package():
    if "AIAssistant" in sys.modules:
        return
    package = types.ModuleType("AIAssistant")
    package.__path__ = [PLUGIN_DIR]
    sys.modules["AIAssistant"] = package
    sys.path.insert(0, os.path.join(ROOT, "tests"))


install_package()
