import math

from . import meshbuild, parts

DEGENERATE_AREA_MM2 = 1e-8
SIZE_TOLERANCE_MM = 0.1
THIN_ERROR = parts.THIN_WALL_ERROR_MM
THIN_WARNING = parts.THIN_WALL_WARNING_MM


def issue(code, message, count=None):
    item = {"code": code, "message": message}
    if count is not None:
        item["count"] = count
    return item


def _triangle_area(p, q, r):
    ux, uy, uz = q[0] - p[0], q[1] - p[1], q[2] - p[2]
    vx, vy, vz = r[0] - p[0], r[1] - p[1], r[2] - p[2]
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    return 0.5 * math.sqrt(nx * nx + ny * ny + nz * nz)


def analyze(mesh):
    degenerate = 0
    volume = 0.0
    directed = {}
    for a, b, c in mesh.triangles:
        p, q, r = mesh.vertices[a], mesh.vertices[b], mesh.vertices[c]
        if a == b or b == c or a == c or _triangle_area(p, q, r) < DEGENERATE_AREA_MM2:
            degenerate += 1
        volume += (p[0] * (q[1] * r[2] - q[2] * r[1]) - p[1] * (q[0] * r[2] - q[2] * r[0])
                   + p[2] * (q[0] * r[1] - q[1] * r[0])) / 6.0
        for u, v in ((a, b), (b, c), (c, a)):
            directed[(u, v)] = directed.get((u, v), 0) + 1
    boundary = 0
    non_manifold = 0
    inconsistent = 0
    seen = set()
    for (u, v), count in directed.items():
        key = (min(u, v), max(u, v))
        if key in seen:
            continue
        seen.add(key)
        forward = directed.get((u, v), 0)
        backward = directed.get((v, u), 0)
        total = forward + backward
        if total == 1:
            boundary += 1
        elif total > 2:
            non_manifold += 1
        elif forward == 2 or backward == 2:
            inconsistent += 1
    return {"degenerate": degenerate, "volume": volume, "boundary_edges": boundary,
            "non_manifold_edges": non_manifold, "inconsistent_edges": inconsistent}


def check(mesh, expected_size=None, min_wall=None, build_volume=None, scene_size=None):
    errors = []
    warnings = []
    mesh = mesh.welded()
    if not mesh.triangles or not mesh.vertices:
        return result_dict(errors + [issue("empty_mesh", "The mesh has no triangles.")], warnings, mesh, None)
    for vertex in mesh.vertices:
        if any(math.isnan(c) or math.isinf(c) for c in vertex):
            return result_dict(errors + [issue("invalid_vertices", "The mesh contains NaN or infinite coordinates.")],
                               warnings, mesh, None)
    stats = analyze(mesh)
    if stats["degenerate"]:
        errors.append(issue("degenerate_triangles", "The mesh has zero-area triangles.", stats["degenerate"]))
    if stats["boundary_edges"]:
        errors.append(issue("not_closed", "The mesh is not closed: some edges belong to one triangle.",
                            stats["boundary_edges"]))
    if stats["non_manifold_edges"]:
        errors.append(issue("non_manifold", "Some edges are shared by more than two triangles.",
                            stats["non_manifold_edges"]))
    if stats["inconsistent_edges"]:
        errors.append(issue("inconsistent_normals", "Neighbouring triangles have opposite orientation.",
                            stats["inconsistent_edges"]))
    if not (stats["boundary_edges"] or stats["non_manifold_edges"] or stats["inconsistent_edges"]):
        if stats["volume"] <= 0:
            errors.append(issue("inward_normals", "The normals point inwards or the volume is zero."))
    size = mesh.size()
    if expected_size is not None:
        for axis, got, want in zip("xyz", size, expected_size):
            if abs(got - want) > SIZE_TOLERANCE_MM:
                errors.append(issue("size_mismatch", "Size along %s is %.3f mm, the specification gives %.3f mm."
                                    % (axis, got, want)))
    if min_wall is not None:
        if min_wall < THIN_ERROR:
            errors.append(issue("wall_too_thin", "The thinnest wall is about %.2f mm, below one extrusion line."
                                % min_wall))
        elif min_wall < THIN_WARNING:
            warnings.append(issue("thin_wall", "The thinnest wall is about %.2f mm, thinner than three 0.4 mm "
                                               "perimeters." % min_wall))
    check_size = scene_size if scene_size is not None else dict(zip("xyz", size))
    fit = None
    if build_volume:
        fit = (check_size["x"] <= build_volume["width"] and check_size["y"] <= build_volume["depth"]
               and check_size["z"] <= build_volume["height"])
        if not fit:
            errors.append(issue("exceeds_build_volume",
                                "The model %.1f x %.1f x %.1f mm does not fit the build volume %.0f x %.0f x %.0f mm."
                                % (check_size["x"], check_size["y"], check_size["z"], build_volume["width"],
                                   build_volume["depth"], build_volume["height"])))
    return result_dict(errors, warnings, mesh, stats, fit)


def result_dict(errors, warnings, mesh, stats, fit=None):
    size = None
    if mesh.vertices:
        size = dict(zip("xyz", [round(v, 3) for v in mesh.size()]))
    result = {
        "valid": not errors,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "warnings": warnings,
        "triangles": len(mesh.triangles),
        "size_mm": size,
        "checks": {
            "closed": bool(stats) and stats["boundary_edges"] == 0 and stats["non_manifold_edges"] == 0,
            "consistent_normals": bool(stats) and stats["inconsistent_edges"] == 0 and stats["volume"] > 0,
            "degenerate_triangles": stats["degenerate"] if stats else None,
            "volume_mm3": round(stats["volume"], 2) if stats else None,
        },
    }
    if fit is not None:
        result["fits_build_volume"] = bool(fit)
    return result


def check_file(path, **kwargs):
    with open(path, "rb") as handle:
        data = handle.read()
    try:
        mesh = meshbuild.read_stl(data)
    except ValueError as e:
        return {"valid": False, "status": "failed", "errors": [issue("unreadable_file", str(e))], "warnings": [],
                "triangles": 0, "size_mm": None, "checks": {}}
    return check(mesh, **kwargs)
