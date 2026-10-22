import unittest
from types import SimpleNamespace

from app.services.routing import haversine_km, optimize_deliveries


class RoutingTests(unittest.TestCase):
    def test_haversine_same_point(self):
        self.assertEqual(haversine_km(-23.55, -46.63, -23.55, -46.63), 0.0)

    def test_optimize_preserves_all_deliveries(self):
        deliveries = [
            SimpleNamespace(id=1, latitude=-23.55, longitude=-46.63),
            SimpleNamespace(id=2, latitude=-23.56, longitude=-46.64),
            SimpleNamespace(id=3, latitude=None, longitude=None),
        ]
        ordered, distance, missing = optimize_deliveries(deliveries)
        self.assertEqual({item.id for item in ordered}, {1, 2, 3})
        self.assertGreater(distance, 0)
        self.assertEqual(missing, [3])


if __name__ == "__main__":
    unittest.main()
