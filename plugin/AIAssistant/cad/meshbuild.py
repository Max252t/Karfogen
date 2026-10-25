import io
import math
import struct
import zipfile

SAMPLES = 36
HOLE_SEGMENTS = 32
WELD_DIGITS = 6
STL_HEADER = b"Karfogen parametric model".ljust(80, b" ")


class Mesh(object):
    def __init__(self):
        self.vertices = []
        self.triangles = []

    def vertex(self, x, y, z):
        self.vertices.append((float(x), float(y), float(z)))
        return len(self.vertices) - 1

    def triangle(self, a, b, c):
        if a == b or b == c or a == c:
            return
        self.triangles.append((a, b, c))

    def extend(self, other):
        offset = len(self.vertices)
        self.vertices.extend(other.vertices)
        self.triangles.extend((a + offset, b + offset, c + offset) for a, b, c in other.triangles)

    def flipped(self):
        result = Mesh()
        result.vertices = list(self.vertices)
        result.triangles = [(a, c, b) for a, b, c in self.triangles]
        return result

    def welded(self):
        result = Mesh()
        lookup = {}
        remap = []
        for x, y, z in self.vertices:
            key = (round(x, WELD_DIGITS) + 0.0, round(y, WELD_DIGITS) + 0.0, round(z, WELD_DIGITS) + 0.0)
            index = lookup.get(key)
            if index is None:
                index = result.vertex(x, y, z)
                lookup[key] = index
            remap.append(index)
        for a, b, c in self.triangles:
            result.triangle(remap[a], remap[b], remap[c])
        return result

    def bounds(self):
        xs = [v[0] for v in self.vertices]
        ys = [v[1] for v in self.vertices]
        zs = [v[2] for v in self.vertices]
        return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))

    def size(self):
        low, high = self.bounds()
        return (high[0] - low[0], high[1] - low[1], high[2] - low[2])


class Apex(object):
    def __init__(self, z):
        self.z = z


class Ring(object):
    def __init__(self, z, radii):
        self.z = z
        self.radii = radii


def circle_radii(radius, samples=SAMPLES):
    return [radius] * samples


def hex_radii(across_flats, samples=SAMPLES):
    apothem = across_flats / 2.0
    radii = []
    for j in range(samples):
        angle = 2.0 * math.pi * j / samples
        local = (angle + math.pi / 6.0) % (math.pi / 3.0) - math.pi / 6.0
        radii.append(apothem / math.cos(local))
    return radii


def revolve(items, closed, samples=SAMPLES):
    mesh = Mesh()
    placed = []
    for item in items:
        if isinstance(item, Apex):
            placed.append(mesh.vertex(0.0, 0.0, item.z))
        else:
            ring = []
            for j in range(samples):
                angle = 2.0 * math.pi * j / samples
                ring.append(mesh.vertex(item.radii[j] * math.cos(angle), item.radii[j] * math.sin(angle), item.z))
            placed.append(ring)
    pairs = list(zip(range(len(items) - 1), range(1, len(items))))
    if closed:
        pairs.append((len(items) - 1, 0))
    for first, second in pairs:
        _connect(mesh, items[first], items[second], placed[first], placed[second], samples)
    return mesh


def _connect(mesh, a_item, b_item, a, b, samples):
    a_apex = isinstance(a_item, Apex)
    b_apex = isinstance(b_item, Apex)
    if a_apex and b_apex:
        raise ValueError("two consecutive apexes")
    if not a_apex and not b_apex and abs(a_item.z - b_item.z) < 1e-9:
        for j in range(samples):
            if abs(a_item.radii[j] - b_item.radii[j]) < 1e-6:
                raise ValueError("flat step with equal radii")
    for j in range(samples):
        k = (j + 1) % samples
        if a_apex:
            mesh.triangle(a, b[k], b[j])
        elif b_apex:
            mesh.triangle(a[j], a[k], b)
        else:
            mesh.triangle(a[j], a[k], b[k])
            mesh.triangle(a[j], b[k], b[j])


def circle_polygon(cx, cy, radius, segments=HOLE_SEGMENTS):
    outer = radius / math.cos(math.pi / segments)
    return [(cx + outer * math.cos(2.0 * math.pi * i / segments), cy + outer * math.sin(2.0 * math.pi * i / segments))
            for i in range(segments)]


def signed_area(points):
    total = 0.0
    for i in range(len(points)):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % len(points)]
        total += x1 * y2 - x2 * y1
    return total / 2.0


def _cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _in_triangle(p, a, b, c):
    d1 = _cross(a, b, p)
    d2 = _cross(b, c, p)
    d3 = _cross(c, a, p)
    return d1 >= 0 and d2 >= 0 and d3 >= 0


def _segments_cross(p1, p2, p3, p4):
    d1 = _cross(p3, p4, p1)
    d2 = _cross(p3, p4, p2)
    d3 = _cross(p1, p2, p3)
    d4 = _cross(p1, p2, p4)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)) and d1 != 0 and d2 != 0 and d3 != 0 and d4 != 0


def _bridge(points, ring, hole):
    start = max(hole, key=lambda i: (points[i][0], -points[i][1]))
    hp = points[start]
    best_x = None
    best_position = None
    for position in range(len(ring)):
        a = points[ring[position]]
        b = points[ring[(position + 1) % len(ring)]]
        if (a[1] - hp[1]) * (b[1] - hp[1]) > 0 or a[1] == b[1]:
            continue
        x = a[0] + (hp[1] - a[1]) / (b[1] - a[1]) * (b[0] - a[0])
        if x < hp[0]:
            continue
        if best_x is None or x < best_x - 1e-12:
            best_x = x
            best_position = position
    if best_position is None:
        raise ValueError("hole is not inside the outline")
    first = best_position
    second = (best_position + 1) % len(ring)
    exact = None
    for position in (first, second):
        p = points[ring[position]]
        if abs(p[1] - hp[1]) < 1e-9 and abs(p[0] - best_x) < 1e-9:
            exact = position
    if exact is not None:
        anchor = exact
    else:
        anchor = first if points[ring[first]][0] > points[ring[second]][0] else second
        corner = points[ring[anchor]]
        crossing = (best_x, hp[1])
        best_angle = None
        for position, index in enumerate(ring):
            p = points[index]
            if p == corner or p[0] < hp[0]:
                continue
            if not (_in_triangle(p, hp, crossing, corner) or _in_triangle(p, crossing, hp, corner)):
                continue
            if _cross(points[ring[position - 1]], p, points[ring[(position + 1) % len(ring)]]) > 0:
                continue
            dx = p[0] - hp[0]
            angle = abs(p[1] - hp[1]) / dx if dx > 0 else float("inf")
            if best_angle is None or angle < best_angle:
                best_angle = angle
                anchor = position
    anchor = _occurrence(points, ring, anchor, hp)
    at = hole.index(start)
    order = hole[at:] + hole[:at]
    return ring[:anchor + 1] + order + [start] + [ring[anchor]] + ring[anchor + 1:]


def _occurrence(points, ring, anchor, target):
    vertex = ring[anchor]
    for position, index in enumerate(ring):
        if index != vertex:
            continue
        prev = points[ring[position - 1]]
        cur = points[index]
        following = points[ring[(position + 1) % len(ring)]]
        before = _cross(prev, cur, target) >= 0
        after = _cross(cur, following, target) >= 0
        if _cross(prev, cur, following) > 0:
            inside = before and after
        else:
            inside = before or after
        if inside:
            return position
    return anchor


def triangulate(outer, holes):
    points = list(outer)
    outer_ids = list(range(len(outer)))
    if signed_area(outer) < 0:
        outer_ids.reverse()
    hole_ids = []
    for hole in holes:
        ids = list(range(len(points), len(points) + len(hole)))
        points.extend(hole)
        if signed_area(hole) > 0:
            ids.reverse()
        hole_ids.append(ids)
    hole_ids.sort(key=lambda ids: -max(points[i][0] for i in ids))
    ring = outer_ids
    for ids in hole_ids:
        ring = _bridge(points, ring, ids)
    return points, _clip(points, ring)


def _clip(points, ring):
    ring = list(ring)
    triangles = []
    guard = 0
    while len(ring) > 3:
        guard += 1
        if guard > 4 * len(points) + 100:
            raise ValueError("triangulation failed")
        count = len(ring)
        reflex = []
        for position in range(count):
            if _cross(points[ring[position - 1]], points[ring[position]], points[ring[(position + 1) % count]]) <= 1e-12:
                reflex.append(ring[position])
        found = None
        fallback = None
        for position in range(count):
            a = ring[position - 1]
            b = ring[position]
            c = ring[(position + 1) % count]
            pa, pb, pc = points[a], points[b], points[c]
            if _cross(pa, pb, pc) <= 1e-12:
                continue
            if fallback is None:
                fallback = position
            blocked = False
            for other in reflex:
                po = points[other]
                if po == pa or po == pb or po == pc:
                    continue
                if _in_triangle(po, pa, pb, pc):
                    blocked = True
                    break
            if not blocked:
                found = position
                break
        if found is None:
            found = fallback
        if found is None:
            raise ValueError("triangulation failed")
        triangles.append((ring[found - 1], ring[found], ring[(found + 1) % count]))
        del ring[found]
    a, b, c = ring
    if _cross(points[a], points[b], points[c]) > 1e-12:
        triangles.append((a, b, c))
    return triangles


def prism(outer, holes, w0, w1, axes, skip_walls=()):
    points, flat = triangulate(outer, holes)
    mesh = Mesh()
    bottom = []
    top = []
    for u, v in points:
        bottom.append(mesh.vertex(*axes(u, v, w0)))
        top.append(mesh.vertex(*axes(u, v, w1)))
    for a, b, c in flat:
        mesh.triangle(top[a], top[b], top[c])
        mesh.triangle(bottom[a], bottom[c], bottom[b])
    loops = [_loop_ids(len(outer), 0, signed_area(outer) < 0)]
    offset = len(outer)
    for hole in holes:
        loops.append(_loop_ids(len(hole), offset, signed_area(hole) > 0))
        offset += len(hole)
    for loop_number, loop in enumerate(loops):
        for position in range(len(loop)):
            if loop_number == 0 and position in skip_walls:
                continue
            i = loop[position]
            j = loop[(position + 1) % len(loop)]
            mesh.triangle(bottom[i], bottom[j], top[j])
            mesh.triangle(bottom[i], top[j], top[i])
    if _determinant(axes) < 0:
        mesh = mesh.flipped()
    return mesh


def _loop_ids(count, offset, reverse):
    ids = [offset + i for i in range(count)]
    if reverse:
        ids.reverse()
    return ids


def _determinant(axes):
    origin = axes(0.0, 0.0, 0.0)
    ex = [p - o for p, o in zip(axes(1.0, 0.0, 0.0), origin)]
    ey = [p - o for p, o in zip(axes(0.0, 1.0, 0.0), origin)]
    ez = [p - o for p, o in zip(axes(0.0, 0.0, 1.0), origin)]
    return (ex[0] * (ey[1] * ez[2] - ey[2] * ez[1]) - ex[1] * (ey[0] * ez[2] - ey[2] * ez[0])
            + ex[2] * (ey[0] * ez[1] - ey[1] * ez[0]))


def rectangle(u0, v0, u1, v1):
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]


def stl_bytes(mesh):
    out = io.BytesIO()
    out.write(STL_HEADER)
    out.write(struct.pack("<I", len(mesh.triangles)))
    for a, b, c in mesh.triangles:
        p, q, r = mesh.vertices[a], mesh.vertices[b], mesh.vertices[c]
        ux, uy, uz = q[0] - p[0], q[1] - p[1], q[2] - p[2]
        vx, vy, vz = r[0] - p[0], r[1] - p[1], r[2] - p[2]
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        out.write(struct.pack("<12fH", nx / length, ny / length, nz / length, p[0], p[1], p[2],
                              q[0], q[1], q[2], r[0], r[1], r[2], 0))
    return out.getvalue()


def read_stl(data):
    if len(data) < 84:
        raise ValueError("file is too short for binary STL")
    count = struct.unpack("<I", data[80:84])[0]
    if len(data) != 84 + 50 * count:
        raise ValueError("file size does not match the triangle count")
    mesh = Mesh()
    lookup = {}
    for index in range(count):
        values = struct.unpack("<12fH", data[84 + 50 * index:134 + 50 * index])
        ids = []
        for corner in range(3):
            point = values[3 + 3 * corner:6 + 3 * corner]
            key = tuple(round(c, WELD_DIGITS - 2) + 0.0 for c in point)
            found = lookup.get(key)
            if found is None:
                found = mesh.vertex(*point)
                lookup[key] = found
            ids.append(found)
        mesh.triangles.append(tuple(ids))
    return mesh


def threemf_bytes(mesh, name):
    rows = ["<vertex x=\"%.6f\" y=\"%.6f\" z=\"%.6f\"/>" % v for v in mesh.vertices]
    faces = ["<triangle v1=\"%d\" v2=\"%d\" v3=\"%d\"/>" % t for t in mesh.triangles]
    model = ("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
             "<model unit=\"millimeter\" xml:lang=\"en-US\" "
             "xmlns=\"http://schemas.microsoft.com/3dmanufacturing/core/2015/02\">\n"
             "<resources><object id=\"1\" type=\"model\" name=\"%s\"><mesh><vertices>%s</vertices>"
             "<triangles>%s</triangles></mesh></object></resources>\n"
             "<build><item objectid=\"1\"/></build></model>\n") % (_xml(name), "".join(rows), "".join(faces))
    content_types = ("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
                     "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">"
                     "<Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>"
                     "<Default Extension=\"model\" ContentType=\"application/vnd.ms-package.3dmanufacturing-3dmodel+xml\"/>"
                     "</Types>")
    rels = ("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
            "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
            "<Relationship Target=\"/3D/3dmodel.model\" Id=\"rel0\" "
            "Type=\"http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel\"/></Relationships>")
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for path, text in (("[Content_Types].xml", content_types), ("_rels/.rels", rels),
                           ("3D/3dmodel.model", model)):
            info = zipfile.ZipInfo(path, (2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, text.encode("utf-8"))
    return out.getvalue()


def _xml(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\"", "&quot;")
