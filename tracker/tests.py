from django.test import TestCase, Client
from django.urls import reverse
from .models import TrackingRecord
from .services import validate_imei, simulate_device_tracking, locate_phone_number, calculate_distance, reverse_geocode_coordinates


class TrackerServiceTests(TestCase):
    def test_validate_imei_valid(self):
        # 15 digits
        valid, clean, note = validate_imei("354595804618131")
        self.assertTrue(valid)
        self.assertEqual(clean, "354595804618131")

    def test_validate_imei_invalid_length(self):
        valid, clean, err = validate_imei("12345")
        self.assertFalse(valid)
        self.assertIn("15 numeric digits", err)

    def test_calculate_distance(self):
        # London to Paris is ~343km
        dist = calculate_distance(51.5074, -0.1278, 48.8566, 2.3522)
        self.assertTrue(330 <= dist <= 360)

    def test_simulate_device_tracking(self):
        result = simulate_device_tracking("android", "354595804618131", "test@gmail.com")
        self.assertTrue(result["success"])
        self.assertIn("latitude", result)
        self.assertIn("longitude", result)
        self.assertIn("steps", result)
        self.assertEqual(len(result["steps"]), 6)

    def test_locate_phone_number_format(self):
        result = locate_phone_number("+254712345678")
        self.assertTrue(result["success"])
        self.assertEqual(result["country_code"], 254)
        self.assertIn("Kenya", result["location_name"])

    def test_reverse_geocode_fallback(self):
        # Coordinates reverse geocode test
        res = reverse_geocode_coordinates(37.7749, -122.4194)
        self.assertTrue(isinstance(res, str))
        self.assertTrue(len(res) > 0)


class TrackerViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.record = TrackingRecord.objects.create(
            target_type='android_imei',
            query_identifier='354595804618131',
            carrier_or_brand='Samsung (Vodafone)',
            device_model='Galaxy S23 Ultra',
            latitude=-1.286389,
            longitude=36.817223,
            location_name='Nairobi, Kenya',
            status='Located'
        )

    def test_dashboard_page(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'IMEI')

    def test_imei_tracker_page(self):
        response = self.client.get(reverse('imei_tracker'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'High-Accuracy Find My Device')

    def test_phone_tracker_page(self):
        response = self.client.get(reverse('phone_tracker'))
        self.assertEqual(response.status_code, 200)

    def test_history_page(self):
        response = self.client.get(reverse('history'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '354595804618131')

    def test_api_track_imei(self):
        response = self.client.post(reverse('api_track_imei'), {
            'device_type': 'android',
            'imei': '355773902211342',
            'account_email': 'test@gmail.com'
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('latitude', data)
        self.assertIn('steps', data)
        self.assertIn('beacon_url', data)
        self.assertIn('beacon_token', data)

    def test_api_sync_device_gps(self):
        response = self.client.post(
            reverse('api_sync_device_gps'),
            data={
                'latitude': 37.7749,
                'longitude': -122.4194,
                'accuracy': 4.5,
                'device_name': 'Test Mobile'
            },
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['accuracy_meters'], int(round(4.5)))
        self.assertIn('google_find_my_url', data)

    def test_beacon_ping_flow(self):
        token = self.record.beacon_token
        # 1. View beacon landing page
        res = self.client.get(reverse('beacon_ping', kwargs={'token': token}))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Find My Device')

        # 2. Report GPS from target device
        report_res = self.client.post(
            reverse('api_beacon_report', kwargs={'token': token}),
            data={
                'latitude': -1.2921,
                'longitude': 36.8219,
                'accuracy': 3.2
            },
            content_type='application/json'
        )
        self.assertEqual(report_res.status_code, 200)
        self.assertTrue(report_res.json()['success'])

        # 3. Check status from dashboard
        status_res = self.client.get(reverse('api_beacon_status', kwargs={'token': token}))
        self.assertEqual(status_res.status_code, 200)
        st_data = status_res.json()
        self.assertTrue(st_data['is_live_gps'])
        self.assertEqual(st_data['accuracy_meters'], 3)

    def test_api_track_phone(self):
        response = self.client.post(reverse('api_track_phone'), {
            'phone_number': '+254722000000',
            'user_location': 'Nairobi'
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('target_lat', data)

    def test_export_csv(self):
        response = self.client.get(reverse('export_csv'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')

    def test_export_json(self):
        response = self.client.get(reverse('export_json'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)
