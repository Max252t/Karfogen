import math
from collections import OrderedDict

SIZES = OrderedDict([
    ("M3", {"d": 3.0, "pitches": [0.5], "head_s": 5.5, "head_k": 2.0, "nut_m": 2.4, "socket_s": 2.5, "cap_d": 5.5, "cs_socket": 2.0,
            "washer": (3.2, 7.0, 0.5)}),
    ("M4", {"d": 4.0, "pitches": [0.7], "head_s": 7.0, "head_k": 2.8, "nut_m": 3.2, "socket_s": 3.0, "cap_d": 7.0, "cs_socket": 2.5,
            "washer": (4.3, 9.0, 0.8)}),
    ("M5", {"d": 5.0, "pitches": [0.8], "head_s": 8.0, "head_k": 3.5, "nut_m": 4.7, "socket_s": 4.0, "cap_d": 8.5, "cs_socket": 3.0,
            "washer": (5.3, 10.0, 1.0)}),
    ("M6", {"d": 6.0, "pitches": [1.0, 0.75], "head_s": 10.0, "head_k": 4.0, "nut_m": 5.2, "socket_s": 5.0, "cap_d": 10.0, "cs_socket": 4.0,
            "washer": (6.4, 12.0, 1.6)}),
    ("M8", {"d": 8.0, "pitches": [1.25, 1.0], "head_s": 13.0, "head_k": 5.3, "nut_m": 6.8, "socket_s": 6.0, "cap_d": 13.0, "cs_socket": 5.0,
            "washer": (8.4, 16.0, 1.6)}),
    ("M10", {"d": 10.0, "pitches": [1.5, 1.25, 1.0], "head_s": 16.0, "head_k": 6.4, "nut_m": 8.4, "socket_s": 8.0, "cap_d": 16.0, "cs_socket": 6.0,
             "washer": (10.5, 20.0, 2.0)}),
    ("M12", {"d": 12.0, "pitches": [1.75, 1.5, 1.25], "head_s": 18.0, "head_k": 7.5, "nut_m": 10.8, "socket_s": 10.0, "cap_d": 18.0, "cs_socket": 8.0,
             "washer": (13.0, 24.0, 2.5)}),
    ("M16", {"d": 16.0, "pitches": [2.0, 1.5], "head_s": 24.0, "head_k": 10.0, "nut_m": 14.8, "socket_s": 14.0, "cap_d": 24.0, "cs_socket": 10.0,
             "washer": (17.0, 30.0, 3.0)}),
    ("M20", {"d": 20.0, "pitches": [2.5, 2.0, 1.5], "head_s": 30.0, "head_k": 12.5, "nut_m": 18.0, "socket_s": 17.0, "cap_d": 30.0, "cs_socket": 12.0,
             "washer": (21.0, 37.0, 3.0)}),
])

SOURCES = {
    "thread": "ISO 261 / ISO 724, metric coarse and fine pitches",
    "bolt": "ISO 4017 hex head, ISO 4762 socket head, ISO 10642 countersunk",
    "nut": "ISO 4032 hex nut",
    "washer": "ISO 7089 plain washer",
}

PROFILE_CREST = 1.0 / 8.0
PROFILE_FLANK = 5.0 / 16.0
PROFILE_ROOT = 1.0 / 4.0
SQRT3 = math.sqrt(3.0)


def size_names():
    return list(SIZES.keys())


def size_data(name):
    return SIZES[name]


def thread_depth(pitch):
    return 5.0 * (SQRT3 / 2.0) * pitch / 8.0


def profile(phase):
    u = (phase + PROFILE_CREST / 2.0) % 1.0
    if u < PROFILE_CREST:
        return 1.0
    u -= PROFILE_CREST
    if u < PROFILE_FLANK:
        return 1.0 - u / PROFILE_FLANK
    u -= PROFILE_FLANK
    if u < PROFILE_ROOT:
        return 0.0
    u -= PROFILE_ROOT
    return u / PROFILE_FLANK


def thread_radius(phase, r_major, pitch):
    r_minor = r_major - thread_depth(pitch)
    return r_minor + (r_major - r_minor) * profile(phase)
