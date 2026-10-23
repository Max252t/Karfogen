import re
import struct

import numpy


def load_stl(path):
    with open(path, "rb") as f:
        data = f.read()
    if data[:5] == b"solid" and b"facet" in data[:1000]:
        found = re.findall(rb"vertex\s+(\S+)\s+(\S+)\s+(\S+)", data)
        tris = numpy.array(found, dtype=float).reshape(-1, 3, 3)
    else:
        count = struct.unpack("<I", data[80:84])[0]
        dt = numpy.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")])
        arr = numpy.frombuffer(data, dtype=dt, count=count, offset=84)
        tris = arr["v"].reshape(-1, 3, 3).astype(float)
    out = numpy.empty_like(tris)
    out[..., 0] = tris[..., 0]
    out[..., 1] = tris[..., 2]
    out[..., 2] = -tris[..., 1]
    return out
