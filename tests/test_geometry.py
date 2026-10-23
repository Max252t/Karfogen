import math
import unittest

import numpy

import support
from AIAssistant.tools import geometry


def box_triangles(w, h, d):
    x, y, z = w / 2.0, h / 2.0, d / 2.0
    v = numpy.array([[-x, -y, -z], [x, -y, -z], [x, y, -z], [-x, y, -z],
                     [-x, -y, z], [x, -y, z], [x, y, z], [-x, y, z]])
    faces = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
             (3, 6, 2), (3, 7, 6), (0, 4, 7), (0, 7, 3), (1, 2, 6), (1, 6, 5)]
    return v[numpy.array(faces)]


def cylinder_triangles(radius, height, segments=64, bore=0.0):
    tris = []
    for i in range(segments):
        a0 = 2 * math.pi * i / segments
        a1 = 2 * math.pi * (i + 1) / segments
        p0 = (radius * math.cos(a0), 0.0, radius * math.sin(a0))
        p1 = (radius * math.cos(a1), 0.0, radius * math.sin(a1))
        q0 = (p0[0], height, p0[2])
        q1 = (p1[0], height, p1[2])
        tris.append([p0, q1, q0])
        tris.append([p0, p1, q1])
        tris.append([(0, 0, 0), p1, p0])
        tris.append([(0, height, 0), q0, q1])
    return numpy.array(tris, dtype=float)


class GeometryTest(unittest.TestCase):
    def test_box_metrics(self):
        tris = box_triangles(10, 20, 30)
        self.assertAlmostEqual(geometry.volume(tris), 6000.0, places=3)
        self.assertAlmostEqual(geometry.surface_area(tris), 2 * (200 + 300 + 600), places=3)
        mn, mx = geometry.bounds(tris)
        self.assertEqual(list(mx - mn), [10, 20, 30])

    def test_box_flat_has_no_overhang(self):
        tris = box_triangles(10, 20, 30)
        result = geometry.evaluate_orientation(tris, geometry.DOWN)
        self.assertEqual(result["overhang_area_mm2"], 0.0)
        self.assertAlmostEqual(result["base_area_mm2"], 300.0, places=1)
        self.assertEqual(result["height_mm"], 20.0)

    def test_suggest_prefers_largest_base_for_stability(self):
        tris = box_triangles(10, 40, 30)
        best = geometry.suggest_orientations(tris, "stability", top=1)[0]
        self.assertAlmostEqual(best["base_area_mm2"], 1200.0, places=1)
        self.assertEqual(best["height_mm"], 10.0)

    def test_cylinder_is_axisymmetric_around_y(self):
        tris = cylinder_triangles(20, 60)
        info = geometry.axisymmetry(tris)
        self.assertTrue(info["is_axisymmetric"])
        self.assertEqual(info["axis"], "y")
        self.assertAlmostEqual(info["diameter_mm"], 40.0, delta=0.5)
        self.assertAlmostEqual(info["aspect"], 1.5, delta=0.05)

    def test_tilted_cylinder_axis_is_found(self):
        tris = cylinder_triangles(20, 60)
        matrix = geometry.rotation_matrix([1.0, 0.0, 1.0], math.radians(30))
        info = geometry.axisymmetry(tris.dot(matrix.T))
        self.assertTrue(info["is_axisymmetric"])
        self.assertEqual(info["axis"], "tilted")
        expected = matrix.dot(numpy.array([0.0, 1.0, 0.0]))
        self.assertAlmostEqual(abs(float(numpy.dot(info["axis_vector"], expected))), 1.0, places=3)
        self.assertAlmostEqual(info["diameter_mm"], 40.0, delta=0.5)
        self.assertAlmostEqual(info["length_mm"], 60.0, delta=0.5)

    def test_world_axis_vector_is_reported(self):
        info = geometry.axisymmetry(cylinder_triangles(20, 60))
        self.assertEqual(info["axis_index"], 1)
        self.assertEqual(info["axis_vector"], [0.0, 1.0, 0.0])

    def test_polygonal_prisms_are_not_bodies_of_revolution(self):
        for sides in (6, 8):
            info = geometry.axisymmetry(cylinder_triangles(20, 60, segments=sides))
            self.assertFalse(info["is_axisymmetric"], sides)

    def test_box_is_not_axisymmetric(self):
        self.assertFalse(geometry.axisymmetry(box_triangles(10, 20, 50))["is_axisymmetric"])

    def test_rotation_to_down(self):
        axis, angle = geometry.rotation_to_down([1.0, 0.0, 0.0])
        matrix = geometry.rotation_matrix(axis, angle)
        rotated = matrix.dot(numpy.array([1.0, 0.0, 0.0]))
        self.assertTrue(numpy.allclose(rotated, [0.0, -1.0, 0.0], atol=1e-9))

    def test_rotation_identity_and_flip(self):
        self.assertEqual(geometry.rotation_to_down([0, -1, 0])[1], 0.0)
        self.assertAlmostEqual(geometry.rotation_to_down([0, 1, 0])[1], math.pi)

    def test_triangles_from_mesh_indexed(self):
        vertices = numpy.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0]], dtype=float)
        tris = geometry.triangles_from_mesh(vertices, [0, 1, 2, 1, 3, 2])
        self.assertEqual(tris.shape, (2, 3, 3))

    def test_analyze_keys(self):
        result = geometry.analyze(cylinder_triangles(10, 30))
        for key in ("size_mm", "volume_cm3", "mean_wall_mm", "current_orientation", "axisymmetry"):
            self.assertIn(key, result)


if __name__ == "__main__":
    unittest.main()
