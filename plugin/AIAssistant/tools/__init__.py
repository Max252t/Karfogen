def register_all():
    from . import settings_tools, scene_tools, slice_tools, advisor_tools, cad_tools
    return [settings_tools, scene_tools, slice_tools, advisor_tools, cad_tools]
