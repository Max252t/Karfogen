import math

from . import meshbuild, threads
from .errors import CadError
from .meshbuild import Apex, Ring, SAMPLES

MAX_TRIANGLES = 300000
THIN_WALL_WARNING_MM = 1.2
THIN_WALL_ERROR_MM = 0.4
SQRT3 = math.sqrt(3.0)
MIN_EDGE_MM = 1.0


def warning(code, message):
    return {"code": code, "message": message}


def _fmt(value):
    return ("%.3f" % value).rstrip("0").rstrip(".")


def _thread_triangle_estimate(length, pitch):
    return int(length / pitch * SAMPLES * SAMPLES * 2) + 4 * SAMPLES


def _fastener_warnings(code_scope, params):
    items = [warning("printer_calibration",
                     "Fit is not guaranteed without calibrating the printer: check a test print and adjust "
                     "clearance_mm.")]
    if code_scope in ("bolt", "nut"):
        items.append(warning("structural_fastener",
                             "A printed plastic fastener is not a replacement for a certified metal fastener "
                             "without engineering calculation and testing."))
    return items


def _label_size(params):
    return "%sx%s" % (params["thread_size"], _fmt(params["pitch_mm"]))


def _chamfered_radii(radii, z, z_end, floor_radius):
    limit = floor_radius + max(0.0, z_end - z)
    return [min(r, limit) for r in radii]


def _thread_rings(z_start, z_end, r_major, pitch, floor_radius):
    rings = []
    step = pitch / SAMPLES
    level = 1
    while True:
        z = z_start + level * step
        if z >= z_end - step * 0.25:
            break
        radii = []
        for j in range(SAMPLES):
            phase = (z - z_start) / pitch - float(j) / SAMPLES
            radii.append(threads.thread_radius(phase, r_major, pitch))
        rings.append(Ring(z, _chamfered_radii(radii, z, z_end, floor_radius)))
        level += 1
    radii = []
    for j in range(SAMPLES):
        phase = (z_end - z_start) / pitch - float(j) / SAMPLES
        radii.append(threads.thread_radius(phase, r_major, pitch))
    rings.append(Ring(z_end, _chamfered_radii(radii, z_end, z_end, floor_radius)))
    return rings


def build_bolt(params):
    data = threads.size_data(params["thread_size"])
    d = data["d"]
    pitch = params["pitch_mm"]
    clearance = params["clearance_mm"]
    length = params["length_mm"]
    depth = threads.thread_depth(pitch)
    r_major = d / 2.0 - clearance
    r_minor = r_major - depth
    head = params["head_type"]
    cosmetic = params["thread_mode"] == "cosmetic"
    warnings = _fastener_warnings("bolt", params)
    if params["load_bearing"]:
        warnings.append(warning("load_bearing_plastic",
                                "The bolt is marked as load bearing: layer adhesion makes printed threads weak "
                                "under tension. Do not use it where failure is dangerous."))
    if pitch < 0.75:
        warnings.append(warning("fine_thread", "Pitch %s mm is close to the limit of FDM printing: the thread may "
                                               "print poorly with a 0.4 mm nozzle." % _fmt(pitch)))
    if cosmetic:
        warnings.append(warning("cosmetic_thread_replaced",
                                "thread_mode=cosmetic: the thread is replaced by a smooth cylinder on the pitch "
                                "diameter. The part cannot be screwed into a thread."))
    items = []
    min_wall = None
    if head == "hex":
        s = data["head_s"]
        k = data["head_k"]
        r0 = 0.95 * s / 2.0
        ch = min(0.12 * k, 0.6)
        items = [Apex(0.0), Ring(0.0, meshbuild.circle_radii(r0)), Ring(ch, meshbuild.hex_radii(s)),
                 Ring(k - ch, meshbuild.hex_radii(s)), Ring(k, meshbuild.circle_radii(r0))]
        z0 = k
        head_height = k
        width = (s, 2.0 * s / SQRT3)
        min_wall = (s / 2.0) - r_major
    elif head == "cylindrical":
        rh = data["cap_d"] / 2.0
        k = d
        ch = min(0.08 * k, 0.5)
        socket = data["socket_s"]
        depth_s = 0.5 * d
        items = [Apex(depth_s), Ring(depth_s, meshbuild.hex_radii(socket)), Ring(0.0, meshbuild.hex_radii(socket)),
                 Ring(0.0, meshbuild.circle_radii(rh - ch)), Ring(ch, meshbuild.circle_radii(rh)),
                 Ring(k - ch, meshbuild.circle_radii(rh)), Ring(k, meshbuild.circle_radii(rh - ch))]
        z0 = k
        head_height = k
        width = (2.0 * rh, 2.0 * rh)
        min_wall = min(k - depth_s, rh - ch - socket / SQRT3)
    else:
        big = 2.0 * d
        cone = big / 2.0 - r_major
        socket = data["cs_socket"]
        depth_s = 0.35 * d
        items = [Apex(depth_s), Ring(depth_s, meshbuild.hex_radii(socket)), Ring(0.0, meshbuild.hex_radii(socket)),
                 Ring(0.0, meshbuild.circle_radii(big / 2.0))]
        z0 = cone
        head_height = cone
        width = (big, big)
        min_wall = min(cone - depth_s, big / 2.0 - depth_s - socket / SQRT3)
    items.append(Ring(z0, meshbuild.circle_radii(r_major)))
    z_end = z0 + length
    if cosmetic:
        r_cos = (r_major + r_minor) / 2.0
        items[-1] = Ring(z0, meshbuild.circle_radii(r_cos))
        items.append(Ring(z_end - depth, meshbuild.circle_radii(r_cos)))
        items.append(Ring(z_end, meshbuild.circle_radii(r_cos - depth * 0.5)))
        items.append(Apex(z_end))
        min_wall = min(min_wall, r_cos)
    else:
        thread_length = params["thread_length_mm"]
        z_thread = z_end - thread_length
        if _thread_triangle_estimate(thread_length, pitch) > MAX_TRIANGLES:
            raise CadError("length_mm", "the threaded length needs more than %d triangles; reduce thread_length_mm "
                                        "or use a larger pitch" % MAX_TRIANGLES)
        if z_thread > z0 + 1e-9:
            items.append(Ring(z_thread, meshbuild.circle_radii(r_major)))
        items.extend(_thread_rings(z_thread, z_end, r_major, pitch, r_minor))
        items.append(Apex(z_end))
        min_wall = min(min_wall, r_minor)
    mesh = meshbuild.revolve(items, False)
    info = {
        "label": "bolt_%s_%s" % (_label_size(params), _fmt(length)),
        "title": "%s bolt %s mm, %s head" % (params["thread_size"], _fmt(length), head),
        "expected_size_mm": (width[0], width[1], head_height + length),
        "min_wall_mm": min_wall,
        "warnings": warnings,
        "compensation": {"clearance_mm": clearance, "applies_to": "thread radius reduced"},
        "nominal": {"thread_size": params["thread_size"], "diameter_mm": d, "pitch_mm": pitch,
                    "length_under_head_mm": length, "head_height_mm": head_height,
                    "major_radius_with_compensation_mm": round(r_major, 4)},
        "printable_thread": not cosmetic,
    }
    return mesh, info


def build_nut(params):
    data = threads.size_data(params["thread_size"])
    d = data["d"]
    pitch = params["pitch_mm"]
    clearance = params["clearance_mm"]
    s = data["head_s"]
    m = params["thickness_mm"]
    depth = threads.thread_depth(pitch)
    r_root = d / 2.0 + clearance
    r0 = 0.95 * s / 2.0
    ch = min(0.1 * m, 0.5)
    lead = r_root + 0.4
    cosmetic = params["thread_mode"] == "cosmetic"
    warnings = _fastener_warnings("nut", params)
    if pitch < 0.75:
        warnings.append(warning("fine_thread", "Pitch %s mm is close to the limit of FDM printing: the thread may "
                                               "print poorly with a 0.4 mm nozzle." % _fmt(pitch)))
    if cosmetic:
        warnings.append(warning("cosmetic_thread_replaced",
                                "thread_mode=cosmetic: the thread is replaced by a smooth bore on the pitch "
                                "diameter. The nut cannot be screwed onto a thread."))
    estimate = _thread_triangle_estimate(m, pitch)
    if estimate > MAX_TRIANGLES:
        raise CadError("thickness_mm", "the thread needs more than %d triangles" % MAX_TRIANGLES)
    items = [Ring(0.0, meshbuild.circle_radii(lead)), Ring(0.0, meshbuild.circle_radii(r0)),
             Ring(ch, meshbuild.hex_radii(s)), Ring(m - ch, meshbuild.hex_radii(s)),
             Ring(m, meshbuild.circle_radii(r0)), Ring(m, meshbuild.circle_radii(lead))]
    if cosmetic:
        r_bore = d / 2.0 - depth * 0.5 + clearance
        items.append(Ring(m - 0.4, meshbuild.circle_radii(r_bore)))
        items.append(Ring(0.4, meshbuild.circle_radii(r_bore)))
    else:
        inner = []
        step = pitch / SAMPLES
        level = 1
        while level * step < m - step * 0.25:
            z = level * step
            radii = []
            for j in range(SAMPLES):
                phase = z / pitch - float(j) / SAMPLES
                radii.append(threads.thread_radius(phase, d / 2.0, pitch) + clearance)
            limit_low = lead - z
            limit_high = lead - (m - z)
            radii = [max(r, limit_low, limit_high) for r in radii]
            inner.append(Ring(z, radii))
            level += 1
        inner.reverse()
        items.extend(inner)
    mesh = meshbuild.revolve(items, True)
    info = {
        "label": "nut_%s" % _label_size(params),
        "title": "%s hex nut, height %s mm" % (params["thread_size"], _fmt(m)),
        "expected_size_mm": (s, 2.0 * s / SQRT3, m),
        "min_wall_mm": s / 2.0 - lead,
        "warnings": warnings,
        "compensation": {"clearance_mm": clearance, "applies_to": "thread bore enlarged"},
        "nominal": {"thread_size": params["thread_size"], "diameter_mm": d, "pitch_mm": pitch,
                    "across_flats_mm": s, "height_mm": m},
        "printable_thread": not cosmetic,
    }
    return mesh, info


def build_washer(params):
    data = threads.size_data(params["thread_size"])
    inner_d, outer_d, standard_h = data["washer"]
    h = params["thickness_mm"]
    clearance = params["clearance_mm"]
    ri = inner_d / 2.0 + clearance
    ro = outer_d / 2.0
    items = [Ring(0.0, meshbuild.circle_radii(ri)), Ring(0.0, meshbuild.circle_radii(ro)),
             Ring(h, meshbuild.circle_radii(ro)), Ring(h, meshbuild.circle_radii(ri))]
    mesh = meshbuild.revolve(items, True)
    info = {
        "label": "washer_%s" % params["thread_size"],
        "title": "%s washer, thickness %s mm" % (params["thread_size"], _fmt(h)),
        "expected_size_mm": (outer_d, outer_d, h),
        "min_wall_mm": min(h, ro - ri),
        "warnings": _fastener_warnings("washer", params),
        "compensation": {"clearance_mm": clearance, "applies_to": "inner hole radius enlarged"},
        "nominal": {"thread_size": params["thread_size"], "inner_diameter_mm": inner_d,
                    "outer_diameter_mm": outer_d, "thickness_mm": h},
        "printable_thread": None,
    }
    return mesh, info


def _hole_radius(diameter, clearance):
    return (diameter + clearance) / 2.0


def build_plate(params):
    width = params["width_mm"]
    depth = params["depth_mm"]
    t = params["thickness_mm"]
    clearance = params["hole_clearance_mm"]
    holes = params["holes"]
    shapes = []
    min_wall = t
    for index, hole in enumerate(holes):
        r = _hole_radius(hole["diameter_mm"], clearance)
        name = "holes[%d]" % index
        edge = min(width / 2.0 - abs(hole["x_mm"]), depth / 2.0 - abs(hole["y_mm"])) - r
        if edge < MIN_EDGE_MM:
            raise CadError(name, "the hole is closer than %g mm to the plate edge or outside it"
                           % MIN_EDGE_MM)
        min_wall = min(min_wall, edge)
        shapes.append((hole["x_mm"], hole["y_mm"], r))
    for i in range(len(shapes)):
        for j in range(i + 1, len(shapes)):
            gap = math.hypot(shapes[i][0] - shapes[j][0], shapes[i][1] - shapes[j][1]) - shapes[i][2] - shapes[j][2]
            if gap < MIN_EDGE_MM:
                raise CadError("holes[%d]" % j, "overlaps or is closer than %g mm to holes[%d]"
                               % (MIN_EDGE_MM, i))
            min_wall = min(min_wall, gap)
    outer = meshbuild.rectangle(-width / 2.0, -depth / 2.0, width / 2.0, depth / 2.0)
    cutouts = [meshbuild.circle_polygon(x, y, r) for x, y, r in shapes]
    mesh = meshbuild.prism(outer, cutouts, 0.0, t, lambda u, v, w: (u, v, w))
    warnings = []
    if holes:
        warnings.append(warning("printer_calibration",
                                "Hole sizes are not guaranteed without calibrating the printer: check a test print "
                                "and adjust hole_clearance_mm."))
    info = {
        "label": "plate_%sx%sx%s" % (_fmt(width), _fmt(depth), _fmt(t)),
        "title": "Plate %s x %s x %s mm, %d holes" % (_fmt(width), _fmt(depth), _fmt(t), len(holes)),
        "expected_size_mm": (width, depth, t),
        "min_wall_mm": min_wall,
        "warnings": warnings,
        "compensation": {"hole_clearance_mm": clearance, "applies_to": "hole diameters enlarged"},
        "nominal": {"width_mm": width, "depth_mm": depth, "thickness_mm": t, "holes": len(holes)},
        "printable_thread": None,
    }
    return mesh, info


def _leg_centers(start, end, count):
    span = (end - start) / float(count)
    return [start + span * (i + 0.5) for i in range(count)], span


def build_bracket(params):
    length = params["length_mm"]
    height = params["height_mm"]
    width = params["width_mm"]
    t = params["thickness_mm"]
    diameter = params["hole_diameter_mm"]
    count = params["holes_per_leg"]
    clearance = params["hole_clearance_mm"]
    if length <= 2.0 * t:
        raise CadError("length_mm", "must be larger than twice the thickness (%g mm)" % (2.0 * t))
    if height <= 2.0 * t:
        raise CadError("height_mm", "must be larger than twice the thickness (%g mm)" % (2.0 * t))
    holes_a = []
    holes_b = []
    r = 0.0
    min_wall = t
    if diameter > 0:
        r = _hole_radius(diameter, clearance)
        margin = MIN_EDGE_MM
        if width / 2.0 - r < margin:
            raise CadError("hole_diameter_mm", "the hole is too large for width_mm: at least %g mm must remain "
                                               "on each side" % margin)
        xs, span_a = _leg_centers(t, length, count)
        zs, span_b = _leg_centers(t, height, count)
        for field, span in (("length_mm", span_a), ("height_mm", span_b)):
            if span < 2.0 * r + 2.0 * margin:
                raise CadError("holes_per_leg", "%d holes of diameter %g do not fit the leg set by %s; reduce the "
                                                "number or diameter" % (count, diameter, field))
        holes_a = [(x, width / 2.0) for x in xs]
        holes_b = [(width / 2.0, z) for z in zs]
        min_wall = min(min_wall, width / 2.0 - r, span_a / 2.0 - r, span_b / 2.0 - r)
    mesh = meshbuild.Mesh()
    horizontal = meshbuild.prism(meshbuild.rectangle(t, 0.0, length, width),
                                 [meshbuild.circle_polygon(x, y, r) for x, y in holes_a], 0.0, t,
                                 lambda u, v, w: (u, v, w), skip_walls=(3,))
    vertical = meshbuild.prism(meshbuild.rectangle(0.0, t, width, height),
                               [meshbuild.circle_polygon(y, z, r) for y, z in holes_b], 0.0, t,
                               lambda u, v, w: (w, u, v), skip_walls=(0,))
    corner = _corner_block(t, width)
    for part in (horizontal, vertical, corner):
        mesh.extend(part)
    mesh = mesh.welded()
    warnings = [warning("bracket_layer_orientation",
                        "With the horizontal leg on the build plate the layers run parallel to the bend, so the "
                        "corner is weak against pulling the legs apart. Check the orientation before slicing.")]
    if diameter > 0:
        warnings.append(warning("printer_calibration",
                                "Hole sizes are not guaranteed without calibrating the printer: check a test print "
                                "and adjust hole_clearance_mm."))
    info = {
        "label": "bracket_%sx%sx%s" % (_fmt(length), _fmt(height), _fmt(width)),
        "title": "Angle bracket %s x %s x %s mm, thickness %s mm" % (_fmt(length), _fmt(height), _fmt(width), _fmt(t)),
        "expected_size_mm": (length, width, height),
        "min_wall_mm": min_wall,
        "warnings": warnings,
        "compensation": {"hole_clearance_mm": clearance, "applies_to": "hole diameters enlarged"},
        "nominal": {"length_mm": length, "height_mm": height, "width_mm": width, "thickness_mm": t,
                    "hole_diameter_mm": diameter, "holes_per_leg": count if diameter > 0 else 0},
        "printable_thread": None,
    }
    return mesh, info


def _corner_block(t, width):
    mesh = meshbuild.Mesh()
    box = meshbuild.prism(meshbuild.rectangle(0.0, 0.0, t, width), [], 0.0, t, lambda u, v, w: (u, v, w))
    keep = meshbuild.Mesh()
    keep.vertices = list(box.vertices)
    for a, b, c in box.triangles:
        pts = [box.vertices[a], box.vertices[b], box.vertices[c]]
        if all(abs(p[0] - t) < 1e-9 for p in pts):
            continue
        if all(abs(p[2] - t) < 1e-9 for p in pts):
            continue
        keep.triangles.append((a, b, c))
    mesh.extend(keep)
    return mesh


BUILDERS = {
    "bolt": build_bolt,
    "nut": build_nut,
    "washer": build_washer,
    "plate": build_plate,
    "bracket": build_bracket,
}


def build(part_type, params):
    mesh, info = BUILDERS[part_type](params)
    min_wall = info["min_wall_mm"]
    if min_wall < THIN_WALL_WARNING_MM:
        info["warnings"].append(warning("thin_wall", "The thinnest wall is about %s mm, thinner than three 0.4 mm "
                                                    "perimeters." % _fmt(min_wall)))
    if len(mesh.triangles) > MAX_TRIANGLES:
        raise CadError("", "the model needs %d triangles, the limit is %d" % (len(mesh.triangles), MAX_TRIANGLES))
    return mesh, info
