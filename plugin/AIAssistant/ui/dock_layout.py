import sys

DEFAULT_SHARE = 0.25
MIN_SHARE = 0.15
MAX_SHARE = 0.4
MAIN_FLOOR_SHARE = 0.5
TOLERANCE = 4
SETTLE_MS = 220
MAIN_PREFS = ("general/window_left", "general/window_top", "general/window_width", "general/window_height")


def clamp_share(share):
    try:
        share = float(share)
    except (TypeError, ValueError):
        return DEFAULT_SHARE
    if share != share:
        return DEFAULT_SHARE
    return max(MIN_SHARE, min(MAX_SHARE, share))


def share_from_legacy(geometry, available_width):
    try:
        width = float(str(geometry).split(",")[2])
    except (IndexError, ValueError):
        return None
    if available_width <= 0 or width <= 0:
        return None
    ratio = width / float(available_width)
    return ratio if MIN_SHARE <= ratio <= 0.4 else None


def shrink(rect, edges):
    x, y, w, h = rect
    left, top, right, bottom = edges
    return (x + left, y + top, w - left - right, h - top - bottom)


def grow(rect, edges):
    return shrink(rect, tuple(-e for e in edges))


def panel_frame_width(available_width, share, panel_min, main_min):
    floor = max(main_min, int(available_width * MAIN_FLOOR_SHARE))
    width = max(panel_min, int(round(available_width * clamp_share(share))))
    width = min(width, available_width - floor)
    return max(width, min(panel_min, available_width // 2))


def dock_layout(available, share, panel_min=0, main_min=0, main_edges=(0, 0, 0, 0), panel_edges=(0, 0, 0, 0)):
    ax, ay, aw, ah = available
    width = panel_frame_width(aw, share, panel_min + panel_edges[0] + panel_edges[2],
                              main_min + main_edges[0] + main_edges[2])
    main_frame = (ax, ay, aw - width, ah)
    panel_frame = (ax + aw - width, ay, width, ah)
    return {"main": shrink(main_frame, main_edges), "panel": shrink(panel_frame, panel_edges),
            "main_frame": main_frame, "panel_frame": panel_frame, "share": width / float(aw) if aw else DEFAULT_SHARE}


def overlaps(first, second):
    return (first[0] < second[0] + second[2] and second[0] < first[0] + first[2] and
            first[1] < second[1] + second[3] and second[1] < first[1] + first[3])


def close(first, second, tolerance=TOLERANCE):
    return first is not None and second is not None and all(abs(a - b) <= tolerance for a, b in zip(first, second))


def user_share(available, sources, main_frame, panel_frame, expected):
    ax, ay, aw, ah = available
    if aw <= 0 or expected is None:
        return None
    if "panel" in sources and abs(panel_frame[0] + panel_frame[2] - (ax + aw)) <= TOLERANCE \
            and abs(panel_frame[2] - expected["panel_frame"][2]) > TOLERANCE:
        return clamp_share(panel_frame[2] / float(aw))
    if "main" in sources and abs(main_frame[0] - ax) <= TOLERANCE \
            and abs(main_frame[2] - expected["main_frame"][2]) > TOLERANCE:
        return clamp_share((ax + aw - main_frame[0] - main_frame[2]) / float(aw))
    return None


def visible_edges(window):
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes
        hwnd = wintypes.HWND(int(window.winId()))
        bounds = wintypes.RECT()
        if ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd, 9, ctypes.byref(bounds), ctypes.sizeof(bounds)) != 0:
            return None
    except Exception:
        return None
    rect = window.geometry()
    edges = (rect.x() - bounds.left, rect.y() - bounds.top, bounds.right - rect.x() - rect.width(),
             bounds.bottom - rect.y() - rect.height())
    if any(e < 0 or e > 96 for e in edges):
        return None
    return edges
