from django.test import SimpleTestCase
from tracker.services import simulate_device_tracking

class RegionTelemetryTests(SimpleTestCase):
    def test_simulate_device_tracking_kenya_region(self):
        """Simulated tracking should return a location within Kenya bounds."""
        result = simulate_device_tracking(
            "android",
            "123456789012345",
            country_or_region="kenya",
            client_timezone=None,
            anchor_coords=None,
        )
        lat, lng = result["latitude"], result["longitude"]
        # Kenya approx latitude -1 to 5, longitude 33 to 43
        self.assertGreaterEqual(lat, -1.0)
        self.assertLessEqual(lat, 5.0)
        self.assertGreaterEqual(lng, 33.0)
        self.assertLessEqual(lng, 43.0)
        self.assertEqual(result["telemetry_mode"], "simulated_cellular")
        self.assertTrue(result["is_simulated"])

    def test_simulate_device_tracking_south_africa_region(self):
        """Simulated tracking should return a location within South Africa bounds."""
        result = simulate_device_tracking(
            "android",
            "987654321098765",
            country_or_region="south africa",
            client_timezone=None,
            anchor_coords=None,
        )
        lat, lng = result["latitude"], result["longitude"]
        # South Africa approx latitude -36 to -22, longitude 15 to 34
        self.assertGreaterEqual(lat, -36)
        self.assertLessEqual(lat, -22)
        self.assertGreaterEqual(lng, 15)
        self.assertLessEqual(lng, 34)
        self.assertEqual(result["telemetry_mode"], "simulated_cellular")
        self.assertTrue(result["is_simulated"])
