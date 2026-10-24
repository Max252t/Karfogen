import math

import numpy

UP = numpy.array([0.0, 1.0, 0.0])
DOWN = numpy.array([0.0, -1.0, 0.0])


def triangles_from_mesh(vertices, indices=None):
    vertices = numpy.asarray(vertices, dtype=numpy.float64)
    if indices is not None and len(indices) > 0:
        idx = numpy.asarray(indices, dtype=numpy.int64).reshape(-1, 3)
        return vertices[idx]
    count = (len(vertices) // 3) * 3
    return vertices[:count].reshape(-1, 3, 3)


def face_data(tris):
    e1 = tris[:, 1] - tris[:, 0]
    e2 = tris[:, 2] - tris[:, 0]
    cross = numpy.cross(e1, e2)
    lengths = numpy.linalg.norm(cross, axis=1)
    areas = lengths / 2.0
    safe = numpy.where(lengths > 1e-12, lengths, 1.0)
    normals = cross / safe[:, None]
    return normals, areas


def bounds(tris):
    pts = tris.reshape(-1, 3)
    return pts.min(axis=0), pts.max(axis=0)


def volume(tris):
    return abs(float(numpy.einsum("ij,ij->i", tris[:, 0], numpy.cross(tris[:, 1], tris[:, 2])).sum()) / 6.0)


def surface_area(tris):
    return float(face_data(tris)[1].sum())


def evaluate_orientation(tris, down, overhang_angle=45.0, plate_tol=0.3, data=None):
    down = numpy.asarray(down, dtype=numpy.float64)
    down = down / numpy.linalg.norm(down)
    normals, areas = data if data is not None else face_data(tris)
    heights = -(tris.reshape(-1, 3).dot(down)).reshape(-1, 3)
    low = heights.min()
    high = heights.max()
    dots = normals.dot(down)
    face_low = heights.max(axis=1)
    on_plate = (dots > 0.99) & (face_low - low < plate_tol)
    threshold = math.sin(math.radians(overhang_angle))
    overhang = (dots > threshold) & (~on_plate)
    total = float(areas.sum())
    base_area = float(areas[on_plate].sum())
    overhang_area = float(areas[overhang].sum())
    return {
        "height_mm": round(float(high - low), 2),
        "base_area_mm2": round(base_area, 1),
        "overhang_area_mm2": round(overhang_area, 1),
        "overhang_ratio": round(overhang_area / total, 4) if total > 0 else 0.0,
        "total_area_mm2": round(total, 1),
    }


def candidate_down_vectors(tris, max_face_candidates=12, data=None):
    normals, areas = data if data is not None else face_data(tris)
    candidates = []

    def add(vec, source):
        vec = numpy.asarray(vec, dtype=numpy.float64)
        n = numpy.linalg.norm(vec)
        if n < 1e-9:
            return
        vec = vec / n
        for existing, _ in candidates:
            if float(existing.dot(vec)) > 0.995:
                return
        candidates.append((vec, source))

    for axis in range(3):
        for sign in (1.0, -1.0):
            vec = numpy.zeros(3)
            vec[axis] = sign
            add(vec, "axis")

    total = float(areas.sum())
    if total > 0:
        quantized = numpy.round(normals * 100).astype(numpy.int64) + 100
        codes = (quantized[:, 0] * 201 + quantized[:, 1]) * 201 + quantized[:, 2]
        unique_codes, first_index, inverse = numpy.unique(codes, return_index=True, return_inverse=True)
        bucket_areas = numpy.bincount(inverse.ravel(), weights=areas, minlength=len(unique_codes))
        order = numpy.argsort(-bucket_areas)
        taken = 0
        for bucket in order:
            area = float(bucket_areas[bucket])
            if taken >= max_face_candidates or area < 0.01 * total:
                break
            add(normals[first_index[bucket]], "face")
            taken += 1
    return candidates


def rotation_to_down(down):
    down = numpy.asarray(down, dtype=numpy.float64)
    down = down / numpy.linalg.norm(down)
    target = DOWN
    dot = float(down.dot(target))
    if dot > 1.0 - 1e-9:
        return numpy.array([0.0, 1.0, 0.0]), 0.0
    if dot < -1.0 + 1e-9:
        return numpy.array([1.0, 0.0, 0.0]), math.pi
    axis = numpy.cross(down, target)
    axis = axis / numpy.linalg.norm(axis)
    return axis, math.acos(max(-1.0, min(1.0, dot)))


def rotation_matrix(axis, angle):
    axis = numpy.asarray(axis, dtype=numpy.float64)
    axis = axis / numpy.linalg.norm(axis)
    x, y, z = axis
    c = math.cos(angle)
    s = math.sin(angle)
    t = 1.0 - c
    return numpy.array([
        [t * x * x + c, t * x * y - s * z, t * x * z + s * y],
        [t * x * y + s * z, t * y * y + c, t * y * z - s * x],
        [t * x * z - s * y, t * y * z + s * x, t * z * z + c],
    ])


def suggest_orientations(tris, goal="balanced", top=3, overhang_angle=45.0):
    data = face_data(tris)
    results = []
    for vec, source in candidate_down_vectors(tris, data=data):
        metrics = evaluate_orientation(tris, vec, overhang_angle=overhang_angle, data=data)
        metrics["down_vector"] = [round(float(v), 4) for v in vec]
        metrics["source"] = source
        results.append(metrics)
    for item in results:
        item["score"] = _score(item, goal)
    results.sort(key=lambda r: r["score"])
    return results[:top]


def _score(m, goal):
    total = max(m["total_area_mm2"], 1.0)
    base_ratio = m["base_area_mm2"] / total
    if goal == "no_supports":
        return m["overhang_ratio"] * 100.0 + m["height_mm"] * 0.02 - base_ratio * 5.0
    if goal == "stability":
        return -base_ratio * 100.0 + m["height_mm"] * 0.05 + m["overhang_ratio"] * 20.0
    if goal == "fast":
        return m["height_mm"] * 0.5 + m["overhang_ratio"] * 30.0
    return m["overhang_ratio"] * 60.0 + m["height_mm"] * 0.03 - base_ratio * 20.0


HARMONICS = tuple(range(1, 9))
WORLD_AXIS_TOLERANCE = 0.999
SYMMETRY_THRESHOLD = 0.08


def _candidate_axes(centroids, areas, total):
    axes = []
    for index in range(3):
        vec = numpy.zeros(3)
        vec[index] = 1.0
        axes.append((vec, index))
    mean = (centroids * areas[:, None]).sum(axis=0) / total
    delta = centroids - mean
    cov = (delta * areas[:, None]).T.dot(delta) / total
    try:
        _, vectors = numpy.linalg.eigh(cov)
    except numpy.linalg.LinAlgError:
        return axes
    for column in range(3):
        vec = vectors[:, column]
        norm = numpy.linalg.norm(vec)
        if norm < 1e-9:
            continue
        vec = vec / norm
        if any(abs(float(vec.dot(world))) > WORLD_AXIS_TOLERANCE for world, _ in axes[:3]):
            continue
        if vec[numpy.argmax(numpy.abs(vec))] < 0:
            vec = -vec
        axes.append((vec, None))
    return axes


def _basis(axis):
    helper = numpy.zeros(3)
    helper[int(numpy.argmin(numpy.abs(axis)))] = 1.0
    e1 = numpy.cross(axis, helper)
    e1 = e1 / numpy.linalg.norm(e1)
    e2 = numpy.cross(axis, e1)
    return e1, e2


def axisymmetry(tris, data=None):
    normals, areas = data if data is not None else face_data(tris)
    total = float(areas.sum())
    if total <= 0:
        return None
    centroids = tris.mean(axis=1)
    pts = tris.reshape(-1, 3)
    best = None
    tilted = None
    for axis, index in _candidate_axes(centroids, areas, total):
        e1, e2 = _basis(axis)
        cu = centroids.dot(e1)
        cv = centroids.dot(e2)
        c0 = float((cu * areas).sum() / total)
        c1 = float((cv * areas).sum() / total)
        u = cu - c0
        v = cv - c1
        phi = numpy.arctan2(v, u)
        score = 0.0
        for k in HARMONICS:
            re = float((areas * numpy.cos(k * phi)).sum())
            im = float((areas * numpy.sin(k * phi)).sum())
            score = max(score, math.hypot(re, im) / total)
        pu = pts.dot(e1) - c0
        pv = pts.dot(e2) - c1
        radius = float(numpy.sqrt(pu * pu + pv * pv).max())
        along = pts.dot(axis)
        length = float(along.max() - along.min())
        nr_u = normals.dot(e1)
        nr_v = normals.dot(e2)
        rlen = numpy.sqrt(u * u + v * v)
        rlen = numpy.where(rlen > 1e-9, rlen, 1.0)
        radial_component = (nr_u * u + nr_v * v) / rlen
        inward = float(areas[radial_component < -0.7].sum()) / total
        lateral = float(areas[numpy.abs(normals.dot(axis)) < 0.1].sum()) / total
        info = {
            "axis": "xyz"[index] if index is not None else "tilted",
            "axis_index": index,
            "axis_vector": [round(float(c), 4) for c in axis],
            "symmetry_error": round(score, 4),
            "radius_mm": round(radius, 2),
            "diameter_mm": round(2 * radius, 2),
            "length_mm": round(length, 2),
            "aspect": round(length / (2 * radius), 3) if radius > 0 else 0.0,
            "inward_area_ratio": round(inward, 4),
            "lateral_area_ratio": round(lateral, 4),
            "center": [round(c0, 2), round(c1, 2)],
        }
        if index is None:
            if tilted is None or info["symmetry_error"] < tilted["symmetry_error"]:
                tilted = info
        elif best is None or info["symmetry_error"] < best["symmetry_error"]:
            best = info
    if tilted is not None and tilted["symmetry_error"] < SYMMETRY_THRESHOLD and tilted["symmetry_error"] < best["symmetry_error"]:
        best = tilted
    best["is_axisymmetric"] = bool(best["symmetry_error"] < SYMMETRY_THRESHOLD)
    best["has_bore"] = bool(best["inward_area_ratio"] > 0.03)
    return best


def analyze(tris, overhang_angle=45.0):
    data = face_data(tris)
    mn, mx = bounds(tris)
    vol = volume(tris)
    area = float(data[1].sum())
    sym = axisymmetry(tris, data=data)
    current = evaluate_orientation(tris, DOWN, overhang_angle=overhang_angle, data=data)
    return {
        "size_mm": [round(float(v), 2) for v in (mx - mn)],
        "volume_cm3": round(vol / 1000.0, 2),
        "surface_area_cm2": round(area / 100.0, 1),
        "mean_wall_mm": round(2.0 * vol / area, 2) if area > 0 else 0.0,
        "triangles": int(len(tris)),
        "current_orientation": current,
        "axisymmetry": sym,
    }
